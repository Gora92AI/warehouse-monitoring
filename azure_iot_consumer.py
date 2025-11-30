"""
Azure IoT Hub Connection Module
Handles real-time data streaming from Azure IoT Hub via Event Hub-compatible endpoint
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from collections import deque
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from azure.eventhub import EventHubConsumerClient
    from azure.eventhub.extensions.checkpointstoreblob import BlobCheckpointStore
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logger.warning("Azure Event Hub SDK not installed. Install with: pip install azure-eventhub")


class AzureIoTHubConsumer:
    """
    Consumer for Azure IoT Hub messages via Event Hub-compatible endpoint.
    
    Usage:
        consumer = AzureIoTHubConsumer(
            connection_string="your-event-hub-compatible-connection-string",
            consumer_group="webappvisualization"
        )
        consumer.start(callback_function)
    """
    
    def __init__(
        self,
        connection_string: str,
        consumer_group: str = "$Default",
        max_buffer_size: int = 1000
    ):
        """
        Initialize the IoT Hub consumer.
        
        Args:
            connection_string: Event Hub-compatible connection string from IoT Hub
            consumer_group: Consumer group name (default: $Default)
            max_buffer_size: Maximum number of messages to buffer
        """
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure Event Hub SDK not available. "
                "Install with: pip install azure-eventhub"
            )
        
        self.connection_string = connection_string
        self.consumer_group = consumer_group
        self.max_buffer_size = max_buffer_size
        
        self.client: Optional[EventHubConsumerClient] = None
        self.data_buffer = deque(maxlen=max_buffer_size)
        self.is_running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.message_count = 0
        self.last_message_time: Optional[datetime] = None
        self.callback: Optional[Callable] = None
        
    def _parse_message(self, event_data) -> Optional[Dict[str, Any]]:
        """
        Parse incoming event data from IoT Hub.
        
        Args:
            event_data: Event data from Event Hub
            
        Returns:
            Parsed message dictionary or None if parsing fails
        """
        try:
            # Get the message body
            body = event_data.body_as_str()
            
            if not body:
                return None
            
            # Parse JSON body
            message = json.loads(body)
            
            # Extract device ID from system properties if available
            device_id = None
            if hasattr(event_data, 'system_properties'):
                system_props = event_data.system_properties
                if system_props:
                    device_id = system_props.get(b'iothub-connection-device-id')
                    if device_id and isinstance(device_id, bytes):
                        device_id = device_id.decode('utf-8')
            
            # If device_id not in system properties, try message body
            if not device_id:
                device_id = message.get('deviceId') or message.get('device_id')
            
            # Build parsed message
            parsed = {
                'timestamp': datetime.now(),
                'device_id': device_id or 'unknown',
                'raw_data': message
            }
            
            # Extract sensor values based on your Arduino message format
            # Station 1: {"deviceId": "station1", "temperature": 25.5, "humidity": 46, "ethylene_ppm": 0.5}
            # Station 2: {"deviceId": "station2", "ethylene_ppm": 0.3}
            
            parsed['temperature_c'] = message.get('temperature') or message.get('temp') or message.get('temperature_c')
            parsed['humidity'] = message.get('humidity') or message.get('hum')
            parsed['ethylene_ppm'] = message.get('ethylene_ppm') or message.get('ethylene') or message.get('c2h4')
            
            # Enqueue time from IoT Hub
            if hasattr(event_data, 'enqueued_time'):
                parsed['enqueued_time'] = event_data.enqueued_time
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
    
    def _on_event(self, partition_context, event):
        """
        Callback for each received event.
        """
        try:
            parsed = self._parse_message(event)
            
            if parsed:
                self.data_buffer.append(parsed)
                self.message_count += 1
                self.last_message_time = datetime.now()
                
                logger.debug(f"Received message from {parsed['device_id']}: {parsed}")
                
                # Call user callback if provided
                if self.callback:
                    self.callback(parsed)
                    
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def _on_partition_initialize(self, partition_context):
        """Called when a partition is initialized."""
        logger.info(f"Partition {partition_context.partition_id} initialized")
    
    def _on_partition_close(self, partition_context, reason):
        """Called when a partition is closed."""
        logger.info(f"Partition {partition_context.partition_id} closed: {reason}")
    
    def _on_error(self, partition_context, error):
        """Called when an error occurs."""
        if partition_context:
            logger.error(f"Error on partition {partition_context.partition_id}: {error}")
        else:
            logger.error(f"Error during load balance: {error}")
    
    def _receive_loop(self):
        """
        Main receive loop running in background thread.
        """
        try:
            self.client = EventHubConsumerClient.from_connection_string(
                conn_str=self.connection_string,
                consumer_group=self.consumer_group
            )
            
            logger.info("Starting to receive messages from IoT Hub...")
            
            with self.client:
                self.client.receive(
                    on_event=self._on_event,
                    on_partition_initialize=self._on_partition_initialize,
                    on_partition_close=self._on_partition_close,
                    on_error=self._on_error,
                    starting_position="-1"  # Start from beginning of stream
                )
                
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.is_running = False
    
    def start(self, callback: Optional[Callable] = None):
        """
        Start receiving messages in background thread.
        
        Args:
            callback: Optional callback function called for each message.
                     Function signature: callback(parsed_message: dict)
        """
        if self.is_running:
            logger.warning("Consumer is already running")
            return
        
        self.callback = callback
        self.is_running = True
        
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        logger.info("IoT Hub consumer started")
    
    def stop(self):
        """Stop receiving messages."""
        self.is_running = False
        
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        logger.info("IoT Hub consumer stopped")
    
    def get_latest_data(self, count: int = 100) -> list:
        """
        Get the latest messages from buffer.
        
        Args:
            count: Number of messages to return
            
        Returns:
            List of parsed messages
        """
        return list(self.data_buffer)[-count:]
    
    def get_latest_by_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest message from a specific device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Latest message from device or None
        """
        for msg in reversed(list(self.data_buffer)):
            if msg.get('device_id') == device_id:
                return msg
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get consumer statistics.
        
        Returns:
            Dictionary with consumer stats
        """
        return {
            'is_running': self.is_running,
            'message_count': self.message_count,
            'buffer_size': len(self.data_buffer),
            'last_message_time': self.last_message_time
        }


# Async version for more advanced use cases
class AsyncAzureIoTHubConsumer:
    """
    Async consumer for Azure IoT Hub messages.
    Use this for async frameworks like FastAPI.
    """
    
    def __init__(
        self,
        connection_string: str,
        consumer_group: str = "$Default",
        max_buffer_size: int = 1000
    ):
        if not AZURE_SDK_AVAILABLE:
            raise ImportError("Azure Event Hub SDK not available")
        
        self.connection_string = connection_string
        self.consumer_group = consumer_group
        self.max_buffer_size = max_buffer_size
        self.data_buffer = deque(maxlen=max_buffer_size)
        self.message_count = 0
        self.last_message_time = None
    
    async def receive_messages(self, callback=None, max_messages=None):
        """
        Receive messages asynchronously.
        
        Args:
            callback: Async callback function
            max_messages: Maximum messages to receive (None for unlimited)
        """
        from azure.eventhub.aio import EventHubConsumerClient as AsyncEventHubConsumerClient
        
        async def on_event(partition_context, event):
            try:
                body = event.body_as_str()
                if body:
                    message = json.loads(body)
                    
                    parsed = {
                        'timestamp': datetime.now(),
                        'device_id': message.get('deviceId', 'unknown'),
                        'temperature_c': message.get('temperature'),
                        'humidity': message.get('humidity'),
                        'ethylene_ppm': message.get('ethylene_ppm'),
                        'raw_data': message
                    }
                    
                    self.data_buffer.append(parsed)
                    self.message_count += 1
                    self.last_message_time = datetime.now()
                    
                    if callback:
                        await callback(parsed)
                        
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        
        client = AsyncEventHubConsumerClient.from_connection_string(
            conn_str=self.connection_string,
            consumer_group=self.consumer_group
        )
        
        async with client:
            await client.receive(
                on_event=on_event,
                starting_position="-1"
            )


def test_connection(connection_string: str, consumer_group: str = "$Default") -> bool:
    """
    Test connection to Azure IoT Hub.
    
    Args:
        connection_string: Event Hub-compatible connection string
        consumer_group: Consumer group name
        
    Returns:
        True if connection successful, False otherwise
    """
    if not AZURE_SDK_AVAILABLE:
        logger.error("Azure SDK not available")
        return False
    
    try:
        client = EventHubConsumerClient.from_connection_string(
            conn_str=connection_string,
            consumer_group=consumer_group
        )
        
        with client:
            partition_ids = client.get_partition_ids()
            logger.info(f"Successfully connected! Partitions: {partition_ids}")
            return True
            
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # Replace with your actual connection string
    CONNECTION_STRING = os.environ.get(
        "AZURE_EVENTHUB_CONNECTION_STRING",
        "Endpoint=sb://your-namespace.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=your-iothub"
    )
    CONSUMER_GROUP = "webappvisualization"
    
    def message_callback(message):
        print(f"Received: {message['device_id']} - Temp: {message.get('temperature_c')}°C, Ethylene: {message.get('ethylene_ppm')} ppm")
    
    # Test connection
    if test_connection(CONNECTION_STRING, CONSUMER_GROUP):
        # Start consumer
        consumer = AzureIoTHubConsumer(CONNECTION_STRING, CONSUMER_GROUP)
        consumer.start(callback=message_callback)
        
        try:
            import time
            while True:
                time.sleep(10)
                stats = consumer.get_stats()
                print(f"Stats: {stats}")
        except KeyboardInterrupt:
            consumer.stop()
