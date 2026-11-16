from pydantic import BaseModel, Field


class DesignationOut(BaseModel):
    system: str
    code: str
    approx: bool


class SteelSummary(BaseModel):
    id: int
    name: str                      # seçilen normdaki ad (system verildiyse) ya da standart ad
    standard_name: str
    matched: DesignationOut | None
    group: str
    group_en: str
    steel_class: str
    alloy_family_id: str | None


class SteelList(BaseModel):
    total: int
    items: list[SteelSummary]


class CompositionOut(BaseModel):
    element: str
    min: float | None
    max: float | None
    nominal: float


class SteelDetail(BaseModel):
    id: int
    standard_name: str
    designations: dict[str, list[DesignationOut]]
    group: str
    group_en: str
    steel_class: str
    class_source: str
    standard_code: str | None
    usage_tr: str | None
    usage_en: str | None
    composition: list[CompositionOut]
    alloy_family_id: str | None
    isopleth_available: bool
    sources: list[str]


class FamilyOut(BaseModel):
    id: str
    base_elements: dict[str, float]
    steel_count: int
    isopleth_available: bool
    calculated_at: str | None


class PointRequest(BaseModel):
    composition: dict[str, float] = Field(..., examples=[{'C': 0.42, 'Mn': 0.75, 'Si': 0.25, 'Cr': 1.05, 'Mo': 0.22}],
                                          description='Ağırlıkça %; Fe kalan')
    T: float = Field(..., ge=300, le=1600, description='Sıcaklık, °C', examples=[760])


class PointResponse(BaseModel):
    T: float
    composition: dict[str, float]
    phases: dict[str, float]                       # kütle kesri
    carbon_in_phases: dict[str, float]             # fazın kendi karbonu, ağ.%
    phase_compositions: dict[str, dict[str, float]]
    phases_considered: list[str]
    ignored_elements: list[str]
    cached: bool
    cache_layer: str | None
    elapsed_ms: float
    model: str
