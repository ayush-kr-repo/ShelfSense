from pydantic import BaseModel, Field
from typing import Optional

# A point in the Image, measured in pixels
class PixelPosition(BaseModel):
    x:int
    y:int

# A point in the real WORLD, measured in metres.
# X=right, Y=up, Z=depth.
class Position(BaseModel):
    x: float
    y: float
    z: float

# The real-world size of a shelf, in metres
class EstimatedDims(BaseModel):
    w: float
    h: float
    d: float

# Overall warehouse size
# relative scale - that's y every field is Optional
class Dimensions(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

from enum import Enum

class ScaleMode(str, Enum):
    reference = "reference"
    full = "full"
    relative = "relative"

class ZoneClass(str, Enum):
    empty = "empty"         # occupancy < 0.2
    low = "low"             # 0.20 - 0.50
    medium = "medium"       # 0.50 - 0.80
    high = "high"           # > 0.80

class Scale(BaseModel):
    mode: ScaleMode
    px_per_m: Optional[float] = None
    confidence: float = Field(ge=0, le=1)

class Shelf(BaseModel):
    id: str
    pixel_position: PixelPosition
    position: Position
    estimated_dims: EstimatedDims
    occupancy_pct: float = Field(ge=0, le=1)
    box_count: int
    capacity_estimate: int
    zone_class: ZoneClass
    empty_zones: list = []
    confidence: float = Field(ge=0, le=1)

# list[list[float]] = a list of points, each point a list of 2 no's
Polygon = list[list[float]]

class FloorPlan(BaseModel):
    total_area: float
    used_area: float
    aisle_regions: list[Polygon] = []
    empty_regions: list[Polygon] = []

class Metadata(BaseModel):
    model_versions: dict = {}
    confidence_summary: float = Field(ge=0, le=1)
    units: str = "metres"

# Whole wrapper
class Warehouse(BaseModel):
    schema_version: str = "1.0"
    warehouse_id: str
    image_count: int
    scale: Scale
    dimensions: Optional[Dimensions] = None     # null when scale is "relative"
    shelves: list[Shelf] = []
    floor_plan: FloorPlan
    metadata: Metadata

class Recommendation(BaseModel):
    condition: str
    recommendation: str
    impact: str

class HealthResult(BaseModel):
    score: float
    band: str
    subscores: dict[str, float]

class Analytics(BaseModel):
    warehouse_id: str
    sur: float
    health: HealthResult
    recommendations: list[Recommendation]

class ShelfSpec(BaseModel):
    id: str
    w: float = Field(gt=0)
    d: float = Field(gt=0)


class OptimizeRequst(BaseModel):
    """The user's constraint form - app.phase 3's input."""
    floor_w_m: float
    floor_d_m: float
    shelves: list[ShelfSpec]
    cell_m: float = Field(default = 0.5, gt=0)
    aisle_m: float = Field(default=0.9, gt=0)
    exit_zone: Optional[list[float]] = None
    time_limit_s: float = Field(default=10, gt=0)

class PlacedShelf(BaseModel):
    """One shelf in the solved layout"""
    id:str
    x:float
    z:float
    w:float
    d:float
    rotated:bool

class Layout(BaseModel):
    """app.phase 3's output: the designed layout"""
    layout_id: Optional[int] = None
    status: str         # OPTIMAL/FEASIBLE/INFEASIBLE
    placed_count:int
    total_requested:int
    shelves: list[PlacedShelf]
