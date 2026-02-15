#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.vyapariq_stack import VyaparIQStack

app = cdk.App()

VyaparIQStack(
    app,
    "VyaparIQMedicalStack",
    description="VyaparIQ Medical Edition - AI-powered inventory management for pharmacies",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth()
