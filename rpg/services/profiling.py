"""
Echoes of Asterra - Runtime Profiling Service
Provides zero-overhead performance timing statistics for engine services.
Active only when config.profiling.enabled is True.
"""
import time
import json
import logging
from typing import Dict, List, Optional
from rpg.config import ProfilingConfig, game_config

logger = logging.getLogger("ProfilingService")


class ProfilingService:
    """
    Measures frame execution timing across registered engine services.
    Exports aggregate metrics to JSON on shutdown.
    """
    def __init__(self, config: Optional[ProfilingConfig] = None) -> None:
        self.config = config or game_config.profiling
        self.enabled = self.config.enabled
        self.export_filepath = self.config.export_filepath
        
        # Timing trackers
        self._start_times: Dict[str, float] = {}
        self._samples: Dict[str, List[float]] = {}
        self._window_size = self.config.sample_window_size

    def start_sample(self, service_name: str) -> None:
        """Public API: Records start timestamp for a service tick."""
        if not self.enabled:
            return
        self._start_times[service_name] = time.perf_counter()

    def end_sample(self, service_name: str) -> None:
        """Public API: Records end timestamp and calculates elapsed milliseconds."""
        if not self.enabled or service_name not in self._start_times:
            return
        elapsed_ms = (time.perf_counter() - self._start_times.pop(service_name)) * 1000.0
        
        if service_name not in self._samples:
            self._samples[service_name] = []
            
        samples = self._samples[service_name]
        samples.append(elapsed_ms)
        if len(samples) > self._window_size:
            samples.pop(0)

    def get_average_ms(self, service_name: str) -> float:
        """Public API: Returns rolling average execution time in milliseconds."""
        samples = self._samples.get(service_name, [])
        if not samples:
            return 0.0
        return sum(samples) / len(samples)

    def export_json(self, filepath: Optional[str] = None) -> None:
        """Public API: Exports collected performance statistics to JSON."""
        if not self.enabled or not self._samples:
            return
            
        target_path = filepath or self.export_filepath
        report = {
            "window_size": self._window_size,
            "services": {}
        }
        for service_name, samples in self._samples.items():
            if samples:
                report["services"][service_name] = {
                    "avg_ms": round(sum(samples) / len(samples), 3),
                    "min_ms": round(min(samples), 3),
                    "max_ms": round(max(samples), 3),
                    "last_ms": round(samples[-1], 3)
                }
                
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info("Exported profiling report to %s", target_path)
        except Exception as e:
            logger.warning("Failed to export profiling report to %s: %s", target_path, e)
