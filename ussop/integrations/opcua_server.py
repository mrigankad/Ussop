"""
OPC-UA Server for Industrial Integration
=========================================
Exposes Ussop inspection results via OPC-UA — the standard industrial
communication protocol for SCADA, MES, and Industry 4.0 systems.

Requires:  pip install asyncua

Node structure:
  Objects/
    Ussop/
      Station_{id}/
        LastDecision       (String)
        LastConfidence     (Float)
        ObjectsFound       (Int32)
        CycleTimeMs        (Float)
        PassCount          (UInt64)
        FailCount          (UInt64)
        UncertainCount     (UInt64)
        PassRate1h         (Float)   — updated every 60 s
        LastInspectionTime (DateTime)
      SystemStatus/
        IsRunning          (Boolean)
        APIVersion         (String)
        UptimeSeconds      (UInt64)
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from asyncua import Server as _OPCServer, ua  # type: ignore
    from asyncua.common.node import Node            # type: ignore
    _OPCUA_AVAILABLE = True
except ImportError:
    _OPCUA_AVAILABLE = False
    logger.debug("[OPC-UA] asyncua not installed. Run: pip install asyncua")

from config.settings import settings


class UssopOpcUaServer:
    """
    OPC-UA server that publishes Ussop inspection data to any
    OPC-UA client (SCADA, Ignition, WinCC, Node-RED, etc.).
    """

    def __init__(self):
        self.available = _OPCUA_AVAILABLE
        self._server: Optional[Any] = None
        self._nodes: Dict[str, Any] = {}          # station_id → dict of node handles
        self._system_nodes: Dict[str, Any] = {}
        self._station_counters: Dict[str, Dict[str, int]] = {}
        self._start_time = time.monotonic()
        self._running = False

    # ── Server lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> bool:
        if not self.available:
            logger.warning("[OPC-UA] asyncua not installed — server disabled")
            return False

        endpoint = f"opc.tcp://{settings.OPCUA_HOST}:{settings.OPCUA_PORT}/ussop"

        try:
            self._server = _OPCServer()
            await self._server.init()

            self._server.set_endpoint(endpoint)
            self._server.set_server_name("Ussop Visual Inspection")

            # Custom namespace
            uri   = "http://ussop.ai/opcua"
            idx   = await self._server.register_namespace(uri)

            # Root object node
            objects = self._server.get_objects_node()
            ussop_obj = await objects.add_object(idx, "Ussop")

            # System status node
            sys_obj = await ussop_obj.add_object(idx, "SystemStatus")
            self._system_nodes = {
                "is_running":  await sys_obj.add_variable(idx, "IsRunning",  True),
                "version":     await sys_obj.add_variable(idx, "APIVersion", settings.APP_VERSION),
                "uptime":      await sys_obj.add_variable(idx, "UptimeSeconds", ua.UInt64(0)),
            }
            await self._system_nodes["is_running"].set_writable()

            self._ussop_obj = ussop_obj
            self._idx = idx

            await self._server.start()
            self._running = True
            logger.info("[OPC-UA] Server started at %s", endpoint)
            return True

        except Exception as exc:
            logger.error("[OPC-UA] Failed to start: %s", exc)
            return False

    async def stop(self):
        if self._server and self._running:
            await self._server.stop()
            self._running = False
            logger.info("[OPC-UA] Server stopped")

    # ── Station management ────────────────────────────────────────────────────

    async def _ensure_station(self, station_id: str):
        """Lazily create OPC-UA nodes for a station on first use."""
        if station_id in self._nodes:
            return

        idx = self._idx
        station_obj = await self._ussop_obj.add_object(idx, f"Station_{station_id}")

        self._nodes[station_id] = {
            "decision":      await station_obj.add_variable(idx, "LastDecision",       "none"),
            "confidence":    await station_obj.add_variable(idx, "LastConfidence",      0.0),
            "objects_found": await station_obj.add_variable(idx, "ObjectsFound",        ua.Int32(0)),
            "cycle_time_ms": await station_obj.add_variable(idx, "CycleTimeMs",         0.0),
            "pass_count":    await station_obj.add_variable(idx, "PassCount",           ua.UInt64(0)),
            "fail_count":    await station_obj.add_variable(idx, "FailCount",           ua.UInt64(0)),
            "uncertain_count": await station_obj.add_variable(idx, "UncertainCount",   ua.UInt64(0)),
            "pass_rate_1h":  await station_obj.add_variable(idx, "PassRate1h",          0.0),
            "last_time":     await station_obj.add_variable(idx, "LastInspectionTime",
                                                             datetime.now(timezone.utc)),
        }
        self._station_counters[station_id] = {"pass": 0, "fail": 0, "uncertain": 0}
        logger.debug("[OPC-UA] Created station node: %s", station_id)

    # ── Data publishing ───────────────────────────────────────────────────────

    async def publish_inspection(self, result: Dict[str, Any]):
        """
        Called after each inspection to push fresh data to OPC-UA clients.
        result dict must have keys: station_id, decision, confidence,
        objects_found, total_time_ms, timestamp.
        """
        if not self._running:
            return

        station_id = result.get("station_id", "default")
        await self._ensure_station(station_id)

        nodes    = self._nodes[station_id]
        counters = self._station_counters[station_id]
        decision = result.get("decision", "unknown")

        # Update counters
        if decision == "pass":
            counters["pass"] += 1
        elif decision == "fail":
            counters["fail"] += 1
        else:
            counters["uncertain"] += 1

        total = counters["pass"] + counters["fail"] + counters["uncertain"]
        pass_rate = counters["pass"] / total if total > 0 else 0.0

        ts = result.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                ts = datetime.now(timezone.utc)
        ts = ts or datetime.now(timezone.utc)

        try:
            await nodes["decision"].write_value(decision)
            await nodes["confidence"].write_value(float(result.get("confidence", 0.0)))
            await nodes["objects_found"].write_value(ua.Int32(result.get("objects_found", 0)))
            await nodes["cycle_time_ms"].write_value(float(result.get("total_time_ms", 0.0)))
            await nodes["pass_count"].write_value(ua.UInt64(counters["pass"]))
            await nodes["fail_count"].write_value(ua.UInt64(counters["fail"]))
            await nodes["uncertain_count"].write_value(ua.UInt64(counters["uncertain"]))
            await nodes["pass_rate_1h"].write_value(pass_rate)
            await nodes["last_time"].write_value(ts)
        except Exception as exc:
            logger.debug("[OPC-UA] Write error: %s", exc)

    async def update_system_status(self):
        """Update uptime and system health nodes."""
        if not self._running:
            return
        try:
            uptime = int(time.monotonic() - self._start_time)
            await self._system_nodes["uptime"].write_value(ua.UInt64(uptime))
        except Exception as exc:
            logger.debug("[OPC-UA] System status update error: %s", exc)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "running":   self._running,
            "endpoint":  f"opc.tcp://{settings.OPCUA_HOST}:{settings.OPCUA_PORT}/ussop" if self.available else None,
            "stations":  list(self._nodes.keys()),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_opcua_server: Optional[UssopOpcUaServer] = None


def get_opcua_server() -> UssopOpcUaServer:
    global _opcua_server
    if _opcua_server is None:
        _opcua_server = UssopOpcUaServer()
    return _opcua_server
