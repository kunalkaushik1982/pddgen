from diagrams import Diagram, Cluster
from diagrams.aws.compute import ECS
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SQS, StepFunctions
from diagrams.aws.ml import Textract, Transcribe, Sagemaker
from diagrams.aws.security import Cognito, IAM
from diagrams.aws.network import CloudFront
from diagrams.aws.general import User

with Diagram("BA Co-Pilot Architecture", show=True):

    user = User("BA User")
    frontend = CloudFront("React App")

    auth = Cognito("Cognito")

    with Cluster("Backend"):
        backend = ECS("FastAPI (ECS)")

    with Cluster("Storage"):
        s3 = S3("S3 Storage")
        db = Dynamodb("DynamoDB")

    with Cluster("Workflow"):
        queue = SQS("SQS")
        workflow = StepFunctions("Step Functions")

    with Cluster("AI Services"):
        textract = Textract("Textract")
        transcribe = Transcribe("Transcribe")
        ai = Sagemaker("Bedrock / AI")

    user >> frontend >> auth >> backend
    backend >> s3
    backend >> db
    backend >> queue >> workflow

    workflow >> [textract, transcribe, ai]

    textract >> s3
    transcribe >> s3
    ai >> s3
