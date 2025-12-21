import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as bedrockagentcore from 'aws-cdk-lib/aws-bedrockagentcore';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class AIOpsStack extends cdk.Stack {
  public readonly investigationsTable: dynamodb.Table;
  public readonly investigationContextTable: dynamodb.Table;
  public readonly logsTable: dynamodb.Table;
  public readonly agentPromptsTable: dynamodb.Table;
  public readonly investigationQueue: sqs.Queue;
  public readonly sqsTriggerFunction: lambda.Function;
  public readonly feishuNotifier: lambda.Function;
  public readonly logsQuery: lambda.Function;
  public readonly xrayGraphQuery: lambda.Function;
  public readonly agentRole: iam.Role;
  public readonly userPool: cognito.UserPool;
  public readonly notificationGateway: bedrockagentcore.CfnGateway;
  public readonly observabilityGateway: bedrockagentcore.CfnGateway;
  public readonly awsOpsGateway: bedrockagentcore.CfnGateway;
  public readonly cloudtrailQuery: lambda.Function;
  public readonly agentRuntime: bedrockagentcore.CfnRuntime;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.investigationsTable = this.createInvestigationsTable();
    this.investigationContextTable = this.createInvestigationContextTable();
    this.logsTable = this.createLogsTable();
    this.agentPromptsTable = this.createAgentPromptsTable();
    this.investigationQueue = this.createInvestigationQueue();
    this.feishuNotifier = this.createFeishuNotifier();
    this.logsQuery = this.createLogsQuery();
    this.xrayGraphQuery = this.createXrayGraphQuery();
    this.cloudtrailQuery = this.createCloudTrailQuery();
    this.agentRole = this.createAgentRole();
    this.userPool = this.createUserPool();
    this.notificationGateway = this.createNotificationGateway();
    this.observabilityGateway = this.createObservabilityGateway();
    this.awsOpsGateway = this.createAwsOpsGateway();
    this.agentRuntime = this.createAgentRuntime();
    this.sqsTriggerFunction = this.createSqsTriggerFunction();
    this.createConfigParameters();
    this.createOutputs();
  }

  private createInvestigationsTable(): dynamodb.Table {
    const table = new dynamodb.Table(this, 'InvestigationsTable', {
      tableName: 'aiops-investigations',
      partitionKey: { name: 'investigation_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'item_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    table.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING }
    });

    return table;
  }

  private createInvestigationContextTable(): dynamodb.Table {
    return new dynamodb.Table(this, 'InvestigationContextTable', {
      tableName: 'aiops-investigation-context',
      partitionKey: { name: 'investigation_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
  }

  private createLogsTable(): dynamodb.Table {
    const table = new dynamodb.Table(this, 'LogsTable', {
      tableName: 'aiops-logs',
      partitionKey: { name: 'component', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'time', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    table.addGlobalSecondaryIndex({
      indexName: 'investigation-id-index',
      partitionKey: { name: 'investigation_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'time', type: dynamodb.AttributeType.STRING }
    });

    return table;
  }

  private createAgentPromptsTable(): dynamodb.Table {
    return new dynamodb.Table(this, 'AgentPromptsTable', {
      partitionKey: { name: 'session_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'agent_name', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
  }

  private createInvestigationQueue(): sqs.Queue {
    return new sqs.Queue(this, 'InvestigationQueue', {
      queueName: 'aiops-investigations.fifo',
      fifo: true,
      contentBasedDeduplication: false,
      visibilityTimeout: cdk.Duration.seconds(120),
      retentionPeriod: cdk.Duration.days(1),
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
  }

  private createLogsQuery(): lambda.Function {
    const fn = new lambda.Function(this, 'LogsQuery', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'logs_query.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(120)
    });

    fn.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['logs:*'],
      resources: ['*']
    }));

    return fn;
  }

  private createXrayGraphQuery(): lambda.Function {
    const fn = new lambda.Function(this, 'XrayGraphQuery', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'xray_graph_query.handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(120)
    });

    fn.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'xray:GetTraceSummaries',
        'xray:BatchGetTraces',
        'xray:GetServiceGraph'
      ],
      resources: ['*']
    }));

    return fn;
  }

  private createCloudTrailQuery(): lambda.Function {
    const fn = new lambda.Function(this, 'CloudTrailQuery', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'cloudtrail_query.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(120)
    });

    fn.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['cloudtrail:LookupEvents'],
      resources: ['*']
    }));

    return fn;
  }

  private createFeishuNotifier(): lambda.Function {
    const configPath = path.join(__dirname, '../../config/.config');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    const feishuWebhookUrl = config.notification_bot;

    return new lambda.Function(this, 'FeishuNotifier', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'feishu_notifier.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(30),
      environment: {
        FEISHU_WEBHOOK_URL: feishuWebhookUrl
      }
    });
  }

  private createAgentRole(): iam.Role {
    const role = new iam.Role(this, 'AIOpsAgentRole', {
      roleName: 'AIOpsAgentRole',
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com')
      ),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ],
      inlinePolicies: {
        DynamoDBAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem',
                'dynamodb:Query', 'dynamodb:Scan'
              ],
              resources: [
                this.investigationsTable.tableArn,
                `${this.investigationsTable.tableArn}/index/*`,
                this.investigationContextTable.tableArn,
                this.logsTable.tableArn,
                this.agentPromptsTable.tableArn
              ]
            })
          ]
        }),
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
              resources: ['*']
            })
          ]
        }),
        ECRAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'ecr:GetAuthorizationToken',
                'ecr:BatchGetImage',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchCheckLayerAvailability'
              ],
              resources: ['*']
            })
          ]
        }),
        LambdaInvoke: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['lambda:InvokeFunction'],
              resources: ['*']
            })
          ]
        }),
        AgentCoreGatewayAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['bedrock-agentcore:InvokeGateway'],
              resources: ['*']
            })
          ]
        }),
        SQSAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'sqs:SendMessage',
                'sqs:ReceiveMessage',
                'sqs:DeleteMessage',
                'sqs:GetQueueAttributes'
              ],
              resources: [this.investigationQueue.queueArn]
            })
          ]
        }),
        XRayAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['xray:PutTraceSegments', 'xray:PutTelemetryRecords'],
              resources: ['*']
            })
          ]
        }),
        AWSResourceReadAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'lambda:ListFunctions',
                'lambda:GetFunction',
                'apigateway:GET',
                'dynamodb:DescribeTable',
                'dynamodb:ListTables',
                'ec2:DescribeInstances',
                'rds:DescribeDBInstances',
                's3:ListBucket',
                's3:GetBucketPolicy'
              ],
              resources: ['*']
            })
          ]
        })
      }
    });

    return role;
  }

  private createUserPool(): cognito.UserPool {
    return new cognito.UserPool(this, 'AIOpsUserPool', {
      userPoolName: 'aiops-users',
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      autoVerify: { email: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
  }

  private createNotificationGateway(): bedrockagentcore.CfnGateway {
    const gateway = new bedrockagentcore.CfnGateway(this, 'NotificationGateway', {
      name: 'aiops-notification',
      authorizerType: 'AWS_IAM',
      protocolType: 'MCP',
      roleArn: this.agentRole.roleArn,
      exceptionLevel: 'DEBUG'
    });

    new bedrockagentcore.CfnGatewayTarget(this, 'FeishuTarget', {
      gatewayIdentifier: gateway.attrGatewayIdentifier,
      name: 'feishu-notifier',
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: this.feishuNotifier.functionArn,
            toolSchema: {
              inlinePayload: [{
                name: 'send_notification',
                description: 'Send notification to Feishu',
                inputSchema: {
                  type: 'object',
                  properties: {
                    message: {
                      type: 'string',
                      description: 'Notification message'
                    }
                  },
                  required: ['message']
                }
              }]
            }
          }
        }
      },
      credentialProviderConfigurations: [{
        credentialProviderType: 'GATEWAY_IAM_ROLE'
      }]
    });

    return gateway;
  }

  private createObservabilityGateway(): bedrockagentcore.CfnGateway {
    const gateway = new bedrockagentcore.CfnGateway(this, 'ObservabilityGateway', {
      name: 'aiops-observability',
      authorizerType: 'AWS_IAM',
      protocolType: 'MCP',
      roleArn: this.agentRole.roleArn,
      exceptionLevel: 'DEBUG'
    });

    new bedrockagentcore.CfnGatewayTarget(this, 'LogsQueryTarget', {
      gatewayIdentifier: gateway.attrGatewayIdentifier,
      name: 'logs-query',
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: this.logsQuery.functionArn,
            toolSchema: {
              inlinePayload: [{
                name: 'query_logs',
                description: 'Query CloudWatch Logs',
                inputSchema: {
                  type: 'object',
                  properties: {
                    log_group_name: {
                      type: 'string',
                      description: 'CloudWatch log group name'
                    },
                    query_string: {
                      type: 'string',
                      description: 'CloudWatch Insights query string'
                    },
                    start_time: {
                      type: 'string',
                      description: 'Start time in epoch seconds'
                    },
                    end_time: {
                      type: 'string',
                      description: 'End time in epoch seconds'
                    }
                  },
                  required: ['log_group_name', 'start_time', 'end_time']
                }
              }]
            }
          }
        }
      },
      credentialProviderConfigurations: [{
        credentialProviderType: 'GATEWAY_IAM_ROLE'
      }]
    });

    new bedrockagentcore.CfnGatewayTarget(this, 'XrayGraphQueryTarget', {
      gatewayIdentifier: gateway.attrGatewayIdentifier,
      name: 'xray-graph-query',
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: this.xrayGraphQuery.functionArn,
            toolSchema: {
              inlinePayload: [{
                name: 'query_trace_graph',
                description: 'Query X-Ray service graph for distributed system topology and service dependencies',
                inputSchema: {
                  type: 'object',
                  properties: {
                    start_time: {
                      type: 'string',
                      description: 'Start time in ISO format (e.g., "2024-01-01T00:00:00Z")'
                    },
                    end_time: {
                      type: 'string',
                      description: 'End time in ISO format (e.g., "2024-01-01T01:00:00Z")'
                    }
                  }
                }
              }]
            }
          }
        }
      },
      credentialProviderConfigurations: [{
        credentialProviderType: 'GATEWAY_IAM_ROLE'
      }]
    });

    return gateway;
  }

  private createAwsOpsGateway(): bedrockagentcore.CfnGateway {
    const gateway = new bedrockagentcore.CfnGateway(this, 'AwsOpsGateway', {
      name: 'aiops-aws-ops',
      authorizerType: 'AWS_IAM',
      protocolType: 'MCP',
      roleArn: this.agentRole.roleArn,
      exceptionLevel: 'DEBUG'
    });

    new bedrockagentcore.CfnGatewayTarget(this, 'CloudTrailQueryTarget', {
      gatewayIdentifier: gateway.attrGatewayIdentifier,
      name: 'cloudtrail-query',
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: this.cloudtrailQuery.functionArn,
            toolSchema: {
              inlinePayload: [{
                name: 'query_cloudtrail',
                description: 'Query CloudTrail events to find who made changes to AWS resources',
                inputSchema: {
                  type: 'object',
                  properties: {
                    resource_name: {
                      type: 'string',
                      description: 'AWS resource name to search for'
                    },
                    resource_type: {
                      type: 'string',
                      description: 'AWS resource type (e.g., AWS::EC2::Instance)'
                    },
                    event_name: {
                      type: 'string',
                      description: 'CloudTrail event name (e.g., RunInstances, TerminateInstances)'
                    },
                    start_time: {
                      type: 'string',
                      description: 'Start time in ISO format (e.g., 2024-01-01T00:00:00Z)'
                    },
                    end_time: {
                      type: 'string',
                      description: 'End time in ISO format (e.g., 2024-01-01T01:00:00Z)'
                    }
                  }
                }
              }]
            }
          }
        }
      },
      credentialProviderConfigurations: [{
        credentialProviderType: 'GATEWAY_IAM_ROLE'
      }]
    });

    return gateway;
  }

  private createAgentRuntime(): bedrockagentcore.CfnRuntime {
    const imageUri = new cdk.CfnParameter(this, 'ImageUri', {
      type: 'String',
      description: 'ECR image URI (e.g., ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPO:latest)'
    });

    return new bedrockagentcore.CfnRuntime(this, 'AIOpsRuntime', {
      agentRuntimeName: 'aiops_runtime',
      roleArn: this.agentRole.roleArn,
      agentRuntimeArtifact: {
        containerConfiguration: {
          containerUri: imageUri.valueAsString,
        }
      },
      environmentVariables: {
        INVESTIGATION_QUEUE_URL: this.investigationQueue.queueUrl,
        INVESTIGATIONS_TABLE: this.investigationsTable.tableName,
        CONTEXT_TABLE: this.investigationContextTable.tableName,
        LOGS_TABLE: this.logsTable.tableName,
        ONLINE_LOG: 'true',
        NOTIFICATION_GATEWAY_URL: this.notificationGateway.attrGatewayUrl,
        OBSERVABILITY_GATEWAY_URL: this.observabilityGateway.attrGatewayUrl,
        AWS_OPS_GATEWAY_URL: this.awsOpsGateway.attrGatewayUrl,
        MAX_TASKS_PER_INVESTIGATION: process.env.MAX_TASKS_PER_INVESTIGATION || '10',
        AWS_REGION: this.region,
        AWS_DEFAULT_REGION: this.region
      },
      networkConfiguration: {
        networkMode: 'PUBLIC'
      }
    });
  }

  private createSqsTriggerFunction(): lambda.Function {
    const fn = new lambda.Function(this, 'SqsTriggerFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'sqs_trigger.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(60),
      environment: {
        AGENT_RUNTIME_ARN: this.agentRuntime.attrAgentRuntimeArn
      }
    });

    fn.addEventSource(new lambdaEventSources.SqsEventSource(this.investigationQueue, {
      batchSize: 1
    }));

    fn.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock-agentcore:InvokeAgentRuntime'],
      resources: ['*']
    }));

    return fn;
  }

  private createConfigParameters(): void {
    new ssm.StringParameter(this, 'ModelConfig', {
      parameterName: '/aiops/config/model',
      stringValue: JSON.stringify({
        default_model: {
          provider: 'bedrock',
          model_id: 'apac.amazon.nova-pro-v1:0',
          region: 'ap-southeast-1'
        }
      })
    });
  }

  private createOutputs(): void {
    new cdk.CfnOutput(this, 'InvestigationsTableName', {
      value: this.investigationsTable.tableName,
      description: 'DynamoDB table for investigations'
    });

    new cdk.CfnOutput(this, 'AgentPromptsTableName', {
      value: this.agentPromptsTable.tableName,
      description: 'DynamoDB table for agent prompts'
    });

    new cdk.CfnOutput(this, 'InvestigationQueueUrl', {
      value: this.investigationQueue.queueUrl,
      description: 'SQS queue URL for investigation triggers'
    });

    new cdk.CfnOutput(this, 'NotificationGatewayUrl', {
      value: this.notificationGateway.attrGatewayUrl,
      description: 'Notification Gateway URL',
      exportName: 'NotificationGatewayUrl'
    });

    new cdk.CfnOutput(this, 'ObservabilityGatewayUrl', {
      value: this.observabilityGateway.attrGatewayUrl,
      description: 'Observability Gateway URL',
      exportName: 'ObservabilityGatewayUrl'
    });

    new cdk.CfnOutput(this, 'AwsOpsGatewayUrl', {
      value: this.awsOpsGateway.attrGatewayUrl,
      description: 'AWS Operations Gateway URL',
      exportName: 'AwsOpsGatewayUrl'
    });

    new cdk.CfnOutput(this, 'AgentRuntimeArn', {
      value: this.agentRuntime.attrAgentRuntimeArn,
      description: 'AgentCore Runtime ARN for AIOps agent'
    });
  }
}
