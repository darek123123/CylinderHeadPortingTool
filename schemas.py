from __future__ import annotations
from typing import Optional, List, Annotated
from pydantic import BaseModel, Field, ConfigDict

# Common helpers
Positive = Annotated[float, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]


# SI models
class MainInputsSI(BaseModel):
    model_config = ConfigDict(extra="allow")
    mach: Annotated[float, Field(ge=0.0, le=1.0)]
    mean_port_area_mm2: Positive
    bore_mm: Positive
    stroke_mm: Positive
    n_cyl: PositiveInt
    ve: Positive = 1.0
    n_ports_eff: Optional[Positive] = None
    cr: Positive = 10.5
    n_int_valves_per_cyl: Optional[PositiveInt] = None
    siamesed_intake: Optional[bool] = False


class FlowRowSI(BaseModel):
    model_config = ConfigDict(extra="allow")
    lift_mm: Positive
    q_in_m3min: NonNegative
    q_ex_m3min: NonNegative
    dp_inH2O: Positive = 28.0
    a_mean_mm2: Optional[Positive] = None
    a_eff_mm2: Optional[Positive] = None
    d_valve_mm: Optional[Positive] = None


class FlowHeaderInputsSI(BaseModel):
    model_config = ConfigDict(extra="allow")
    in_width_mm: Positive
    in_height_mm: Positive
    in_r_top_mm: NonNegative
    in_r_bot_mm: NonNegative
    ex_width_mm: Positive
    ex_height_mm: Positive
    ex_r_top_mm: NonNegative
    ex_r_bot_mm: NonNegative
    d_valve_in_mm: Positive
    d_valve_ex_mm: Positive
    # Optional detailed geometry (align with IOP):
    d_stem_in_mm: Optional[Positive] = None
    d_stem_ex_mm: Optional[Positive] = None
    d_throat_in_mm: Optional[Positive] = None
    d_throat_ex_mm: Optional[Positive] = None
    seat_angle_in_deg: Optional[float] = None
    seat_angle_ex_deg: Optional[float] = None
    seat_width_in_mm: Optional[NonNegative] = None
    seat_width_ex_mm: Optional[NonNegative] = None
    # Optional port descriptors (page 1 of IOP):
    port_volume_cc: Optional[Positive] = None
    port_length_centerline_mm: Optional[Positive] = None
    port_area_mm2: Optional[Positive] = None
    cr: Positive
    max_lift_mm: Positive
    rows_in: List[dict]
    rows_ex: List[dict]
    ex_pipe_used: Optional[bool] = False


# US models
class MainInputsUS(BaseModel):
    model_config = ConfigDict(extra="allow")
    mach: Annotated[float, Field(ge=0.0, le=1.0)]
    mean_port_area_in2: Positive
    bore_in: Positive
    stroke_in: Positive
    n_cyl: PositiveInt
    ve: Positive = 1.0
    n_ports_eff: Optional[Positive] = None
    cr: Positive = 10.5
    n_int_valves_per_cyl: Optional[PositiveInt] = None
    siamesed_intake: Optional[bool] = False


class FlowRowUS(BaseModel):
    model_config = ConfigDict(extra="allow")
    lift_in: Positive
    q_cfm: NonNegative
    dp_inH2O: Positive = 28.0
    a_mean_in2: Optional[Positive] = None
    a_eff_in2: Optional[Positive] = None
    d_valve_in: Optional[Positive] = None


class FlowHeaderInputsUS(BaseModel):
    model_config = ConfigDict(extra="allow")
    # geometric fields in mm (as our SI packers expect); keep symmetry for now
    in_width_mm: Positive = 0.0  # if not used, can be 0 in US fixtures
    in_height_mm: Positive = 0.0
    in_r_top_mm: NonNegative = 0.0
    in_r_bot_mm: NonNegative = 0.0
    ex_width_mm: Positive = 0.0
    ex_height_mm: Positive = 0.0
    ex_r_top_mm: NonNegative = 0.0
    ex_r_bot_mm: NonNegative = 0.0
    d_valve_in_mm: Positive = 0.0
    d_valve_ex_mm: Positive = 0.0
    cr: Positive
    max_lift_mm: Positive
    rows_in: List[dict]
    rows_ex: List[dict]
    ex_pipe_used: Optional[bool] = False


class ValveSeatParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat_angle_deg: Annotated[float, Field(ge=15.0, le=75.0)]
    seat_width_mm: Positive

