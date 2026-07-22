from re import M
from typing import Literal

from pydantic import BaseModel, ValidationError

class Bar:
    def __init__(self, name) -> None:
        self.name = name

    def prt_name(self, msg):
        print(f"{self.name} {msg}")

obj = Bar("gsc")


class Car(BaseModel):
    model_name: str
    year: int
    car_type: Literal["suv", "sedan", "pickup"]

try:
    my_data = '{"model_name": "x7", "year": 2016, "car_type": "suv", "new_type": "aaa"}'
    obj = Car.model_validate_json(my_data)
    print(f"type: {type(obj.model_dump())}", obj.model_dump())
    print("\n\n")
    print(f"type: {type(obj.model_dump_json())}", obj.model_dump_json())
    print(obj.schema_json())
#    obj = Car(model_name="x7", year=2026, car_type="suv")

except ValidationError:
    print("예외 발생했음")