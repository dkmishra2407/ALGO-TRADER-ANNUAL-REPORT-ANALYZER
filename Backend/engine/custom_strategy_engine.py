import backtrader as bt
import tempfile
import os
import importlib.util
import sys

def create_custom_strategy(strategy_code: str, strategy_name: str):
    """
    Create a custom strategy from code string
    """
    # Create a temporary file for the strategy
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(strategy_code)
        temp_file = f.name

    try:
        # Load the module
        spec = importlib.util.spec_from_file_location(strategy_name, temp_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the strategy class (any class that inherits from bt.Strategy)
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, bt.Strategy) and
                attr != bt.Strategy):
                strategy_class = attr
                break

        if strategy_class is None:
            raise ValueError("No class inheriting from bt.Strategy found in the code")

        return strategy_class

    except Exception as e:
        raise ValueError(f"Error loading custom strategy: {str(e)}")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass

def save_custom_strategy(strategy_code: str, strategy_name: str):
    """
    Save custom strategy to strategies directory
    """
    strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'strategies')
    os.makedirs(strategies_dir, exist_ok=True)

    file_path = os.path.join(strategies_dir, f"{strategy_name}_strategy.py")

    with open(file_path, 'w') as f:
        f.write(strategy_code)

    return file_path