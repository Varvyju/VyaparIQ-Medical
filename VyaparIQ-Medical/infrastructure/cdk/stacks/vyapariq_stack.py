from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_s3_notifications as s3n,
)
from constructs import Construct

class VyaparIQStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Tables
        inventory_table = dynamodb.Table(
            self, "InventoryTable",
            table_name="VyaparIQ-Inventory",
            partition_key=dynamodb.Attribute(
                name="medicine_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True
        )

        alerts_table = dynamodb.Table(
            self, "AlertsTable",
            table_name="VyaparIQ-Alerts",
            partition_key=dynamodb.Attribute(
                name="alert_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="VyaparIQ-PurchaseOrders",
            partition_key=dynamodb.Attribute(
                name="order_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # S3 Buckets
        shelf_images_bucket = s3.Bucket(
            self, "ShelfImagesBucket",
            bucket_name="vyapariq-shelf-images",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),
                    enabled=True
                )
            ]
        )

        prescriptions_bucket = s3.Bucket(
            self, "PrescriptionsBucket",
            bucket_name="vyapariq-prescriptions",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),
                    enabled=True
                )
            ]
        )

        # IAM Role for Lambda functions
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Grant Bedrock permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )

        # Grant DynamoDB permissions
        inventory_table.grant_read_write_data(lambda_role)
        alerts_table.grant_read_write_data(lambda_role)
        orders_table.grant_read_write_data(lambda_role)

        # Grant S3 permissions
        shelf_images_bucket.grant_read(lambda_role)
        prescriptions_bucket.grant_read(lambda_role)

        # Lambda Functions
        analyze_shelf_function = lambda_.Function(
            self, "AnalyzeShelfFunction",
            function_name="VyaparIQ-AnalyzeShelf",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../../src/lambda/analyze_shelf"),
            timeout=Duration.seconds(30),
            memory_size=512,
            role=lambda_role,
            environment={
                "DYNAMODB_INVENTORY_TABLE": inventory_table.table_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            }
        )

        # Add Function URL
        analyze_shelf_url = analyze_shelf_function.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.POST],
                allowed_headers=["*"]
            )
        )

        # S3 trigger for shelf images
        shelf_images_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(analyze_shelf_function)
        )

        process_expiry_function = lambda_.Function(
            self, "ProcessExpiryFunction",
            function_name="VyaparIQ-ProcessExpiry",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../../src/lambda/process_expiry"),
            timeout=Duration.seconds(60),
            memory_size=256,
            role=lambda_role,
            environment={
                "DYNAMODB_INVENTORY_TABLE": inventory_table.table_name,
                "DYNAMODB_ALERTS_TABLE": alerts_table.table_name
            }
        )

        # Schedule daily at 6 AM IST (00:30 UTC)
        rule = events.Rule(
            self, "DailyExpiryCheck",
            schedule=events.Schedule.cron(minute="30", hour="0")
        )
        rule.add_target(targets.LambdaFunction(process_expiry_function))

        check_interactions_function = lambda_.Function(
            self, "CheckInteractionsFunction",
            function_name="VyaparIQ-CheckInteractions",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../../src/lambda/check_interactions"),
            timeout=Duration.seconds(30),
            memory_size=256,
            role=lambda_role,
            environment={
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            }
        )

        check_interactions_url = check_interactions_function.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.POST],
                allowed_headers=["*"]
            )
        )

        generate_order_function = lambda_.Function(
            self, "GenerateOrderFunction",
            function_name="VyaparIQ-GenerateOrder",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../../src/lambda/generate_order"),
            timeout=Duration.seconds(30),
            memory_size=512,
            role=lambda_role,
            environment={
                "DYNAMODB_ORDERS_TABLE": orders_table.table_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            }
        )

        generate_order_url = generate_order_function.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.POST],
                allowed_headers=["*"]
            )
        )

        # Outputs
        from aws_cdk import CfnOutput

        CfnOutput(self, "AnalyzeShelfURL", value=analyze_shelf_url.url)
        CfnOutput(self, "CheckInteractionsURL", value=check_interactions_url.url)
        CfnOutput(self, "GenerateOrderURL", value=generate_order_url.url)
        CfnOutput(self, "ShelfImagesBucket", value=shelf_images_bucket.bucket_name)
        CfnOutput(self, "PrescriptionsBucket", value=prescriptions_bucket.bucket_name)
