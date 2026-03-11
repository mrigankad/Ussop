"""
Modbus TCP Server for PLC Integration
Implements a Modbus slave that exposes inspection data to PLCs
"""
import asyncio
import struct
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from pymodbus.server import StartAsyncTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
    from pymodbus.device import ModbusDeviceIdentification
    Pymodbus_AVAILABLE = True
except ImportError:
    Pymodbus_AVAILABLE = False
    print("[Modbus] pymodbus not installed. Run: pip install pymodbus")

from ussop.config.settings import settings


class UssopModbusServer:
    """
    Modbus TCP server for PLC integration.
    
    Register Map:
    Coils (0x):
      0001: Trigger inspection (write 1 to trigger)
      0002: Pass signal (read-only)
      0003: Fail signal (read-only)
      0004: System ready (read-only)
    
    Input Registers (3x):
      3001: Result code (0=none, 1=pass, 2=fail, 3=error)
      3002: Defect count
      3003-3006: Defect class IDs (up to 4)
      3007-3008: Processing time (ms, split into 2 registers)
    
    Holding Registers (4x):
      4001: Command register
      4002: Station ID selector
    """
    
    def __init__(self, inspection_callback=None):
        self.inspection_callback = inspection_callback
        self.last_result: Optional[Dict[str, Any]] = None
        self.server = None
        self.context = None
        
        if not Pymodbus_AVAILABLE:
            raise ImportError("pymodbus not installed")
        
        self._init_datastore()
    
    def _init_datastore(self):
        """Initialize Modbus data store."""
        # Coils: 1-10 (10 coils)
        self.coils = ModbusSequentialDataBlock(1, [False] * 10)
        
        # Discrete Inputs: 1-10 (10 inputs)
        self.discrete_inputs = ModbusSequentialDataBlock(1, [False] * 10)
        
        # Input Registers: 3001-3020 (20 registers)
        self.input_registers = ModbusSequentialDataBlock(1, [0] * 20)
        
        # Holding Registers: 4001-4020 (20 registers)
        self.holding_registers = ModbusSequentialDataBlock(1, [0] * 20)
        
        # Create slave context
        self.store = ModbusSlaveContext(
            di=self.discrete_inputs,
            co=self.coils,
            hr=self.holding_registers,
            ir=self.input_registers
        )
        
        self.context = ModbusServerContext(slaves=self.store, single=True)
        
        # Device identification
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'Ussop'
        self.identity.ProductCode = 'Ussop-VI'
        self.identity.VendorUrl = 'https://ussop.ai'
        self.identity.ProductName = 'Ussop Visual Inspector'
        self.identity.ModelName = 'Ussop v1.0'
        self.identity.MajorMinorRevision = '1.0'
    
    async def start(self):
        """Start the Modbus server."""
        print(f"[Modbus] Starting server on {settings.MODBUS_HOST}:{settings.MODBUS_PORT}")
        
        # Set system ready
        self.coils.setValues(4, [True])
        
        # Start polling for trigger
        asyncio.create_task(self._poll_trigger())
        
        # Start server
        self.server = await StartAsyncTcpServer(
            self.context,
            identity=self.identity,
            address=(settings.MODBUS_HOST, settings.MODBUS_PORT)
        )
    
    async def _poll_trigger(self):
        """Poll for trigger coil and run inspection."""
        last_trigger = False
        
        while True:
            try:
                # Read trigger coil (address 1)
                trigger = self.coils.getValues(1, 1)[0]
                
                if trigger and not last_trigger:
                    # Rising edge - trigger inspection
                    print("[Modbus] Trigger detected, running inspection...")
                    await self._run_inspection()
                    
                    # Clear trigger
                    self.coils.setValues(1, [False])
                
                last_trigger = trigger
                await asyncio.sleep(0.05)  # 50ms poll rate
                
            except Exception as e:
                print(f"[Modbus] Poll error: {e}")
                await asyncio.sleep(1)
    
    async def _run_inspection(self):
        """Run inspection and update registers."""
        # Clear previous results
        self.coils.setValues(2, [False])  # Pass
        self.coils.setValues(3, [False])  # Fail
        self.input_registers.setValues(1, [0] * 20)  # Clear registers
        
        try:
            if self.inspection_callback:
                result = await self.inspection_callback()
                self._update_registers(result)
            else:
                print("[Modbus] No inspection callback registered")
                
        except Exception as e:
            print(f"[Modbus] Inspection error: {e}")
            # Set error code
            self.input_registers.setValues(1, [3])  # Error
    
    def _update_registers(self, result: Dict[str, Any]):
        """Update Modbus registers with inspection result."""
        self.last_result = result
        
        # Map decision to code
        decision_map = {'pass': 1, 'fail': 2, 'uncertain': 2}
        result_code = decision_map.get(result.get('decision'), 0)
        
        # Set coils
        if result.get('decision') == 'pass':
            self.coils.setValues(2, [True])   # Pass
            self.coils.setValues(3, [False])  # Fail
        else:
            self.coils.setValues(2, [False])  # Pass
            self.coils.setValues(3, [True])   # Fail
        
        # Set input registers
        registers = [0] * 20
        registers[0] = result_code
        registers[1] = result.get('objects_found', 0)
        
        # Defect class IDs (up to 4)
        detections = result.get('detections', [])
        for i, det in enumerate(detections[:4]):
            registers[2 + i] = det.get('class_label', 0)
        
        # Processing time (split 32-bit into 2 registers)
        time_ms = int(result.get('total_time_ms', 0))
        registers[6] = time_ms & 0xFFFF  # Low word
        registers[7] = (time_ms >> 16) & 0xFFFF  # High word
        
        self.input_registers.setValues(1, registers)
        
        print(f"[Modbus] Registers updated: result={result_code}, defects={len(detections)}")
    
    def get_register_values(self) -> Dict[str, Any]:
        """Get current register values for debugging."""
        return {
            'coils': self.coils.getValues(1, 10),
            'input_registers': self.input_registers.getValues(1, 20),
            'holding_registers': self.holding_registers.getValues(1, 20),
        }
    
    async def stop(self):
        """Stop the Modbus server."""
        if self.server:
            self.server.shutdown()
            print("[Modbus] Server stopped")


# Singleton instance
_modbus_server: Optional[UssopModbusServer] = None


def get_modbus_server(inspection_callback=None) -> UssopModbusServer:
    """Get or create Modbus server singleton."""
    global _modbus_server
    if _modbus_server is None:
        _modbus_server = UssopModbusServer(inspection_callback)
    return _modbus_server


# Example usage
if __name__ == "__main__":
    async def mock_inspection():
        """Mock inspection for testing."""
        import random
        await asyncio.sleep(0.5)
        return {
            'decision': random.choice(['pass', 'fail']),
            'objects_found': random.randint(0, 3),
            'detections': [{'class_label': i+1} for i in range(random.randint(0, 3))],
            'total_time_ms': 850
        }
    
    async def main():
        server = get_modbus_server(mock_inspection)
        await server.start()
    
    asyncio.run(main())
