import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';

export class EcrStack extends cdk.Stack {
  public readonly repository: ecr.Repository;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.repository = new ecr.Repository(this, 'AIOpsAgentRepo', {
      repositoryName: `${this.stackName.toLowerCase()}-aiops-agent`,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: this.repository.repositoryUri,
      description: 'ECR Repository URI'
    });

    new cdk.CfnOutput(this, 'RepositoryName', {
      value: this.repository.repositoryName,
      description: 'ECR Repository Name'
    });
  }
}
