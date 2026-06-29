import backtrader as bt
import tempfile
import os
import importlib.util
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# AWS S3 setup
AWS_STRATEGY_BUCKET = os.getenv("AWS_STRATEGY_BUCKET", "algo-trader-strategies")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def get_s3_client():
    return boto3.client('s3', region_name=AWS_REGION)


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
    Save custom strategy to AWS S3, or fall back to a local file if S3 is unavailable.
    """
    try:
        s3_client = get_s3_client()
        key = f"strategies/{strategy_name}_strategy.py"
        s3_client.put_object(
            Bucket=AWS_STRATEGY_BUCKET,
            Key=key,
            Body=strategy_code,
            ContentType='text/plain'
        )
        return f"s3://{AWS_STRATEGY_BUCKET}/{key}"
    except Exception as e:
        strategy_dir = os.path.join(BASE_DIR, "strategies")
        os.makedirs(strategy_dir, exist_ok=True)
        local_path = os.path.join(strategy_dir, f"{strategy_name}_strategy.py")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(strategy_code)
        print(f"AWS S3 unavailable ({e}); saved strategy locally at {local_path}")
        return f"local://{local_path}"

def load_custom_strategy_code(strategy_name: str):
    """
    Load custom strategy code from AWS S3
    """
    try:
        s3_client = get_s3_client()
        key = f"strategies/{strategy_name}_strategy.py"
        response = s3_client.get_object(Bucket=AWS_STRATEGY_BUCKET, Key=key)
        return response['Body'].read().decode('utf-8')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise ValueError(f"Error loading strategy from AWS S3: {str(e)}")

def list_custom_strategies_from_s3():
    """
    List custom strategies stored in AWS S3
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=AWS_STRATEGY_BUCKET, Prefix='strategies/')
        if 'Contents' not in response:
            return []
        
        strategies = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('_strategy.py'):
                strategy_name = key.replace('strategies/', '').replace('_strategy.py', '')
                strategies.append(strategy_name)
        return strategies
    except ClientError as e:
        print(f"Error listing strategies from S3: {e}")
        return []