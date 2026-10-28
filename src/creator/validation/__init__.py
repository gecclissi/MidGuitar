"""Validador de exportação (MIDI, songs.dta, .mogg e pacote completo por destino)."""
from src.creator.validation.issues import Issue, has_errors
from src.creator.validation.profiles import PROFILES, TargetProfile
from src.creator.validation.midi_rules import midi_track_names, validate_midi
from src.creator.validation.dta_parser import DtaSyntaxError, parse_dta
from src.creator.validation.dta_rules import validate_dta
from src.creator.validation.mogg_rules import MoggInfo, read_mogg_info, validate_mogg
from src.creator.validation.targets import detect_target, validate_export
from src.creator.validation.report import format_issues_for_dialog

__all__ = ["Issue", "has_errors", "TargetProfile", "PROFILES", "validate_midi",
           "midi_track_names", "parse_dta", "DtaSyntaxError", "validate_dta",
           "MoggInfo", "read_mogg_info", "validate_mogg", "validate_export",
           "detect_target", "format_issues_for_dialog"]
