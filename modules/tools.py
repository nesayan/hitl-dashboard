from langchain_core.tools import StructuredTool

# Tool 1: Add Two Numbers

def _add_two_numbers(a: float, b: float) -> float:
    """Use this tool to add two numbers and return the result."""
    return a + b

add_two_numbers = StructuredTool.from_function(
    func=_add_two_numbers,
    name="add_two_numbers",
    description="Add two numbers and return the result.",
    metadata={"requires_approval": False},
)

# Tool 2: Subtract Two Numbers

def _subtract_two_numbers(a: float, b: float) -> float:
    """Use this tool to subtract two numbers and return the result."""
    return a - b

subtract_two_numbers = StructuredTool.from_function(
    func=_subtract_two_numbers,
    name="subtract_two_numbers",
    description="Subtract two numbers and return the result.",
    metadata={"requires_approval": True},
)

# Tool 3: Get Details About Sayan

def _get_details_about_sayan() -> dict:
    """Use this tool to get details about Sayan."""
    return {
        "name": "Sayan",
        "age": 30,
        "occupation": "Software Engineer"
    }

get_details_about_sayan = StructuredTool.from_function(
    func=_get_details_about_sayan,
    name="get_details_about_sayan",
    description="Get details about Sayan.",
    metadata={"requires_approval": False},
)

