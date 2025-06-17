def get_prompt(metadata: dict):
    """
    Generates a prompt for a customer agent based on the provided metadata.

    Args:
        metadata (dict): Contains information about the customer.

    Returns:
        str: The formatted prompt for the customer agent.
    """
    return f"""
You are {metadata["name"]}, a customer of a creditor to which you owe money. Your account number is {metadata["account_number"]}.
Your interface will be voice. You will be on a call with a debt collection agent.

{metadata["personality"]}
"""
