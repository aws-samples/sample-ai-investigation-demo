#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { AIOpsStack } from '../lib/aiops-stack';
import { EcrStack } from '../lib/ecr-stack';
import { STACK_NAME_PREFIX } from '../lib/const';

const app = new cdk.App();

new EcrStack(app, `${STACK_NAME_PREFIX}-ecr`, {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION 
  }
});

new AIOpsStack(app, `${STACK_NAME_PREFIX}-main`, {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION 
  }
});