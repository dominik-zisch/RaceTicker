"""Data ingestion module."""

from .parser import RaceState, RunnerState
from .csv_fetcher import get_race_state, get_fetch_status, start_csv_poller
