from altk.pre_tool.toolguard.toolguard.data_types import Domain, ToolPolicyItem
from mellea import generative


@generative
def tool_policy_pseudo_code(
    policy_item: ToolPolicyItem, fn_to_analyze: str, domain: Domain
) -> str:
    """
        Returns a pseudo code to check business constraints on a tool cool using an API

        Args:
            policy_item (ToolPolicyItem): Business policy, in natural language, specifying a constraint on a process involving the tool under analysis.
            fn_to_analyze (str): The function signature of the tool under analysis.
            domain (Domain): Python code defining available data types and APIs for invoking other tools.

        Returns:
            str: A pseudo code descibing how to use the API to check the tool call

        * The available API functions are listed in the `domain.app_api.content`.
        * Analyze the API functions' signatures (input and output parameter types).
        * You cannot assume other API functions.
        * For data objects (dataclasses or Pydantic models), only reference the explicitly declared fields.
            * Do not assume the presence of any additional fields.
            * Do not assume any implicit logic or relationships between field values (e.g., naming conventions).
        * List all the required API calls to check the business constraints.
        * If some information is missing, you should call another api function declared in the domain API.

        Examples:
    ```python
        domain = {
            "app_types": {
                "file_name": "car_types.py",
                "content": '''
                    class CarType(Enum):
                        SEDAN = "sedan"
                        SUV = "suv"
                        VAN = "van"
                    class Car:
                        plate_num: str
                        car_type: CarType
                    class Person:
                        id: str
                        driving_licence: str
                    class Insurance:
                        doc_id: str
                    class CarOwnership:
                        owenr_id: str
                        start_date: str
                        end_date: str
                '''
            },
            "app_api": {
                "file_name": "cars_api.py",
                "content": '''
                    class CarAPI(ABC):
                        def buy_car(self, plate_num: str, owner_id: str, insurance_id: str): pass
                        def get_person(self, id: str) -> Person: pass
                        def get_insurance(self, id: str) -> Insurance: pass
                        def get_car(self, plate_num: str) -> Car: pass
                        def car_ownership_history(self, plate_num: str) -> List[CarOwnership]: pass
                        def delete_car(self, plate_num: str): pass
                        def list_all_cars_owned_by(self, id: str) -> List[Car]: pass
                        def are_relatives(self, person1_id: str, person2_id: str) -> bool: pass
                '''
            }
        }
    ```
    * Example 1:
    ```
        tool_policy_pseudo_code(
            {"name": "documents exists", "description": "when buying a car, check that the car owner has a driving licence and that the insurance is valid."},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        )
    ```
    may return:
    ```
        assert api.get_person(owner_id).driving_licence
        assert api.get_insurance(insurance_id)
    ```

    * Example 2:
    ```
        tool_policy_pseudo_code(
            {"name": "has driving licence", "description": "when buying a car, check that the car owner has a driving licence"},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        )
    ```
        may return:
    ```
        assert api.get_insurance(insurance_id)
    ```

    * Example 3:
    ```
        tool_policy_pseudo_code(
            {"name": "no transfers on holidays", "description": "when buying a car, check that it is not a holiday today"},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        )
    ```
        should return an empty string.

    * Example 4:
    ```
        tool_policy_pseudo_code(
            {"name": "Not in the same family",
            "description": "when buying a van, check that the van was never owned by someone from the buyer's family."},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        )
    ```
        should return:
    ```
        car = api.get_car(plate_num)
        if car.car_type == CarType.VAN:
            history = api.car_ownership_history(plate_num)
            for each ownership in history:
                assert(not api.are_relatives(ownership.owenr_id, owner_id))
    ```
    """
    ...
