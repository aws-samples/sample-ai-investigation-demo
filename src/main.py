"""
Main entry point for AIOps workflow
Enhanced with trace-based logging support
"""

from graph import stream_graph_updates
from langchain_core.messages import HumanMessage
import os

# Import centralized logging and trace context
from logging_config import get_main_logger
from trace_context import start_trace_session, end_trace_session, get_current_trace_id

def process_input(user_input, trace_id=None):
    """
    Process user input and return the results
    
    Args:
        user_input (str): The user's input text (alarm description or query)
        trace_id (str): Optional trace ID for this processing session
        
    Returns:
        dict: The results of the analysis
    """
    # Start trace session if not provided
    if trace_id is None:
        trace_id = start_trace_session()
    else:
        start_trace_session(trace_id)
    
    # Initialize logger with trace context
    logger = get_main_logger()
    
    logger.info(f"Processing input with trace ID: {trace_id}")
    logger.info(f"Input: {user_input[:100]}...")
    
    try:
        # Use the existing stream_graph_updates function with return_result=True
        result = stream_graph_updates(user_input, return_result=True)
        logger.info("Input processing completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error processing input: {e}", exc_info=True)
        raise
    finally:
        # End trace session
        ended_trace_id = end_trace_session()
        logger.info(f"Completed trace session: {ended_trace_id}")

# Sample CloudWatch alert descriptions
SAMPLE_ALERTS = [
    """
ALARM: "High CPU Utilization" in US West (Oregon)
Threshold Crossed: 1 datapoint [90.25 (22/05/25 06:15:00)] was greater than the threshold (80.0).
Alarm Details:
- Name: High-CPU-Alarm
- Description: EC2 instance i-0515355a75c579ece has high CPU utilization
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:15:00Z
- AWS Account: 613477150601
- Region: ap-southeast-1
- Dimensions: InstanceId=i-0515355a75c579ece
    """,
    """
ALARM: "Low Free Storage Space" in US West (Oregon)
Threshold Crossed: 1 datapoint [9.2 (22/05/25 06:10:00)] was less than the threshold (10.0).
Alarm Details:
- Name: Low-Storage-Alarm
- Description: RDS instance database-1 is running low on free storage space
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:10:00Z
- AWS Account: 123456789012
- Region: us-west-2
- Dimensions: DBInstanceIdentifier=database-1
    """,
    """
ALARM: "High Error Rate" in US West (Oregon)
Threshold Crossed: 3 datapoints [12.5 (22/05/25 06:05:00), 15.3 (22/05/25 06:10:00), 18.7 (22/05/25 06:15:00)] was greater than the threshold (5.0).
Alarm Details:
- Name: API-Error-Rate-Alarm
- Description: API Gateway endpoint /api/v1/orders is experiencing high error rates
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:15:00Z
- AWS Account: 123456789012
- Region: us-west-2
- Dimensions: ApiName=OrdersAPI, Stage=prod, Method=POST
    """,
    """
CRITICAL ALARM: "Database Connection Failure" in US East (N. Virginia)
Threshold Crossed: 5 consecutive datapoints [100.0 (22/05/25 06:00:00), 100.0 (22/05/25 06:01:00), 100.0 (22/05/25 06:02:00), 100.0 (22/05/25 06:03:00), 100.0 (22/05/25 06:04:00)] was greater than the threshold (0.0).
Alarm Details:
- Name: Database-Connection-Failure-Alarm
- Description: CRITICAL - Production database is unreachable
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:04:00Z
- AWS Account: 123456789012
- Region: us-east-1
- Dimensions: DBInstanceIdentifier=prod-main-db
    """,
    """
ALARM: "High Exception Rate in Application Logs" in US East (N. Virginia)
Threshold Crossed: 10 datapoints in the last 5 minutes exceeded the threshold (5 exceptions per minute).
Alarm Details:
- Name: Application-Exception-Alarm
- Description: High rate of NullPointerException in checkout service
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:10:00Z
- AWS Account: 123456789012
- Region: us-east-1
- Dimensions: ServiceName=checkout-service, LogGroup=/aws/lambda/checkout-processor
- Log Pattern: "NullPointerException at com.example.checkout.PaymentProcessor"
    """,
    """
ALARM: "demo-app experience high error" in Asia Pacific (Singapore)
Threshold: The alarm is in the ALARM state when the metric is GreaterThanThreshold 0.2 for at least 1 of the last 1 period(s) of 60 seconds.
Alarm Details:
- Name:                       demo-app experience high error
- Description:                
- State Change:               OK -> ALARM
- Reason for State Change:    Threshold Crossed: 1 out of the last 1 datapoints [0.5555555555555556 (29/05/25 15:37:00)] was greater than the threshold (0.2) (minimum 1 datapoint for OK -> ALARM transition).
- Timestamp:                  Thursday 29 May, 2025 15:38:48 UTC
- AWS Account:                613477150601
- Alarm Arn:                  arn:aws:cloudwatch:ap-southeast-1:613477150601:alarm:Service Error Rate Too High
    """
]


# Main interaction loop
def main():
    """Main CLI interaction loop with trace support"""
    # Start a session trace for the entire CLI session
    session_trace_id = start_trace_session()
    logger = get_main_logger()
    
    logger.info(f"Starting AIOps Workflow CLI with session trace ID: {session_trace_id}")
    print("AIOps Workflow with CloudWatch Alerts and Decision-Based Routing")
    print(f"Session Trace ID: {session_trace_id}")
    print("Options:")
    print("1. Enter custom CloudWatch alert")
    print("2. Use sample CPU utilization alert (Resource path)")
    print("3. Use sample storage space alert (Resource path)")
    print("4. Use sample API error rate alert (Trace path with critical notification)")
    print("5. Use sample critical database failure alert (Resource path with critical notification)")
    print("6. Use sample application exception alert (Trace path)")
    print("7. Use real error sample")
    print("q. Quit")
    
    while True:
        try:
            choice = input("\nEnter your choice: ")
            logger.info(f"User selected choice: {choice}")
            
            if choice.lower() in ["quit", "exit", "q"]:
                logger.info("User chose to quit")
                print("Goodbye!")
                break
                
            # Generate a new trace ID for each analysis
            analysis_trace_id = start_trace_session()
            logger.info(f"Starting new analysis with trace ID: {analysis_trace_id}")
            print(f"\nStarting analysis with trace ID: {analysis_trace_id}")
            
            if choice == "1":
                print("Enter CloudWatch alert description (type 'END' on a new line when finished):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                user_input = "\n".join(lines)
                logger.info(f"Processing custom alert: {user_input[:100]}...")
                stream_graph_updates(user_input)
            elif choice == "2":
                logger.info("Processing sample CPU utilization alert")
                print("Using sample CPU utilization alert...")
                stream_graph_updates(SAMPLE_ALERTS[0])
            elif choice == "3":
                logger.info("Processing sample storage space alert")
                print("Using sample storage space alert...")
                stream_graph_updates(SAMPLE_ALERTS[1])
            elif choice == "4":
                logger.info("Processing sample API error rate alert")
                print("Using sample API error rate alert...")
                stream_graph_updates(SAMPLE_ALERTS[2])
            elif choice == "5":
                logger.info("Processing sample critical database failure alert")
                print("Using sample critical database failure alert...")
                stream_graph_updates(SAMPLE_ALERTS[3])
            elif choice == "6":
                logger.info("Processing sample application exception alert")
                print("Using sample application exception alert...")
                stream_graph_updates(SAMPLE_ALERTS[4])
            elif choice == "7":
                logger.info("Processing real error sample")
                print("Real Error...")
                stream_graph_updates(SAMPLE_ALERTS[5])
            else:
                logger.warning(f"Invalid choice entered: {choice}")
                print("Invalid choice. Please try again.")
                continue
            
            # End the analysis trace
            completed_trace_id = end_trace_session()
            logger.info(f"Completed analysis trace: {completed_trace_id}")
            print(f"Analysis completed. Logs saved to trace: {completed_trace_id}")
                
        except KeyboardInterrupt:
            logger.info("User interrupted with Ctrl+C")
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            print(f"Error: {e}")
            # Fallback to sample alert
            print("Using fallback sample alert...")
            try:
                logger.info("Attempting fallback to sample alert")
                stream_graph_updates(SAMPLE_ALERTS[0])
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}", exc_info=True)
                print(f"Fallback also failed: {e2}")
            break
    
    # End the session trace
    ended_session_trace_id = end_trace_session()
    logger.info(f"Ending CLI session trace: {ended_session_trace_id}")


# Generate and save graph visualization
def generate_graph_visualization():
    """Generate graph visualization with trace logging"""
    logger = get_main_logger()
    
    try:
        from IPython.display import Image, display
        from graph import graph
        
        logger.info("Generating graph visualization")
        png_data = graph.get_graph().draw_mermaid_png()
        with open('graph.png', 'wb') as f:
            f.write(png_data)
        
        logger.info("Graph visualization saved to graph.png")
        
        # Display the graph image when in a notebook environment
        try:
            display(Image('graph.png'))
        except:
            pass
        
    except Exception as e:
        logger.warning(f"Could not generate graph visualization: {e}")


if __name__ == "__main__":
    logger = get_main_logger()
    logger.info("Generating graph visualization and starting main application")
    generate_graph_visualization()
    main()
