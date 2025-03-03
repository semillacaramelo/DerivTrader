"""
API Connection Module for Deriv Trading Bot.

This module handles establishing and maintaining connections to the Deriv API,
with support for both demo and real accounts.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import json
import time
import uuid
import random
import re
from typing import Dict, Any, Optional, Union, List

import websockets

from modules.logger import setup_logger
import config
from utils.validators import validate_api_token
from utils.helpers import extract_error_message

logger = setup_logger('api_connection')

class DerivAPIConnection:
    """
    Manages the connection to Deriv's API and provides methods for interacting with it.

    This class handles authentication, reconnection, and provides a clean interface
    for making API requests to Deriv.
    """

    def __init__(self, use_demo: Optional[bool] = None):
        """
        Initialize the API connection.

        Args:
            use_demo (bool, optional): Whether to use the demo account.
                If None, will use the DEFAULT_ACCOUNT_TYPE from config.
        """
        # Determine if we should use demo account based on input or config
        if use_demo is None:
            self.is_demo = config.DEFAULT_ACCOUNT_TYPE == "demo"
        else:
            self.is_demo = use_demo

        # Select appropriate token
        self.api_token = config.DERIV_API_TOKEN if self.is_demo else config.DERIV_API_TOKEN_REAL
        self.app_id = config.APP_ID

        # Set endpoint - Using official production endpoint
        self.endpoint = "wss://ws.binaryws.com/websockets/v3"

        # Initialize connection state variables
        self.websocket = None
        self.is_connected = False
        self.connection_attempts = 0
        self.last_ping_time = 0
        self.account_info = None
        self.req_id_to_response = {}
        self.pending_requests = {}
        self.subscriptions = {}

        # Simulation mode
        self.simulation_mode = False

        logger.info(f"Initialized API connection for {'demo' if self.is_demo else 'real'} account")
        if self.simulation_mode:
            logger.warning("SIMULATION MODE ENABLED: Using simulated API responses instead of real API connection")

    def _is_placeholder_token(self, token: str) -> bool:
        """Check if the token is a placeholder for development/testing purposes."""
        return len(token) == 15 and token.isalnum()

    async def connect(self) -> bool:
        """Establish a connection to the Deriv API following official documentation."""
        if not self.api_token:
            logger.error("API token is empty. Cannot connect.")
            return False

        if self.simulation_mode:
            logger.warning("SIMULATION MODE: Simulating successful connection to Deriv API")
            self.is_connected = True
            self.connection_attempts = 0
            self.last_ping_time = time.time()
            await self._setup_simulated_account()
            return True

        try:
            # Include app_id in initial connection URL as required by Deriv API
            base_url = f"{self.endpoint}?app_id={self.app_id}"
            logger.info(f"Connecting to Deriv API ({base_url})...")
            
            try:
                self.websocket = await websockets.connect(
                    base_url,
                    ssl=True,
                    compression=None,
                    max_size=config.MAX_MESSAGE_SIZE
                )
            except Exception as e:
                logger.error(f"Initial connection failed: {e}")
                return False

            # Start message handler
            asyncio.create_task(self._message_handler())
            # Start ping handler to keep connection alive
            asyncio.create_task(self._ping_handler())

            # Send authorize request
            auth_response = await self._send_request({
                "authorize": self.api_token
            })

            if 'error' in auth_response:
                error_msg = auth_response['error'].get('message', 'Unknown error')
                error_code = auth_response['error'].get('code', '')
                logger.error(f"Authentication failed: {error_msg} (Code: {error_code})")
                await self.disconnect()
                return False

            self.account_info = auth_response
            self.is_connected = True
            self.connection_attempts = 0
            self.last_ping_time = time.time()

            # Log successful connection details
            account = auth_response.get('authorize', {})
            account_type = "Demo" if self.is_demo else "Real"
            balance = account.get('balance', 'Unknown')
            currency = account.get('currency', 'USD')
            logger.info(f"Successfully connected to {account_type} account {account.get('loginid')}. Balance: {balance} {currency}")

            return True

        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            await self.disconnect()
            return False

    async def _setup_simulated_account(self):
        """Set up simulated account information for testing."""
        account_type = "demo" if self.is_demo else "real"

        self.account_info = {
            "authorize": {
                "email": f"simulated_{account_type}_user@example.com",
                "currency": "USD",
                "balance": 10000.00,
                "name": "Simulated Trader",
                "loginid": f"VRTC{random.randint(100000, 999999)}",
                "is_virtual": True,
                "account_category": "virtual",
                "country": "us",
                "landing_company_name": "virtual",
                "landing_company_shortcode": "vrtc",
                "local_currencies": {"USD": {"fractional_digits": 2}},
                "preferred_language": "EN",
                "user_id": random.randint(1000000, 9999999),
                "account_opening_reason": "Trading",
            },
            "echo_req": {
                "authorize": self.api_token
            },
            "msg_type": "authorize"
        }

        logger.info(f"Simulated account created: {self.account_info['authorize']['loginid']} with ${self.account_info['authorize']['balance']}")

    async def _simulated_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simulated response for the given request."""
        # Extract request type
        req_type = next((k for k in request.keys() if k not in ('req_id', 'app_id')), None)
        req_id = request.get('req_id', str(uuid.uuid4()))

        # Default response structure
        response = {
            "req_id": req_id,
            "echo_req": request
        }

        # Handle different request types
        if req_type == "ping":
            response["ping"] = "pong"
            response["msg_type"] = "ping"

        elif req_type == "authorize":
            # Return the cached account info
            return self.account_info

        elif req_type == "proposal":
            # Simulate a trading proposal
            symbol = request.get("proposal", {}).get("symbol", "1HZ100V")
            contract_type = request.get("proposal", {}).get("contract_type", "CALL")
            currency = request.get("proposal", {}).get("currency", "USD")
            amount = float(request.get("proposal", {}).get("amount", 10))

            response["proposal"] = {
                "id": f"d1e8eb1d-3ce3-c218-{random.randint(10000, 99999)}",
                "price": round(random.uniform(amount * 0.5, amount * 1.5), 2),
                "date_expiry": int(time.time()) + 3600,
                "date_start": int(time.time()),
                "display_value": f"${amount:.2f}",
                "payout": amount * 2,
                "spot": round(random.uniform(1000, 2000), 2),
                "spot_time": int(time.time()) - 10,
                "symbol": symbol,
                "contract_type": contract_type,
                "currency": currency
            }
            response["msg_type"] = "proposal"

        elif req_type == "ticks":
            # Simulate tick data
            symbol = request.get("ticks")
            current_spot = random.uniform(1000, 2000)
            response["tick"] = {
                "ask": current_spot + 0.1,
                "bid": current_spot - 0.1,
                "epoch": int(time.time()),
                "id": f"df8b73d5-84c7-b211-{random.randint(10000, 99999)}",
                "quote": current_spot,
                "symbol": symbol
            }
            response["msg_type"] = "tick"

        elif req_type == "ticks_history":
            # Simulate historical tick data
            symbol = request.get("ticks_history")
            count = request.get("count", 10)
            end = request.get("end", "latest")

            # Generate mock historical data
            prices = []
            times = []
            now = int(time.time())

            # Generate timestamps and prices
            for i in range(count):
                times.append(now - (count - i) * 60)  # One minute intervals
                prices.append(round(random.uniform(1000, 2000), 2))

            response["history"] = {
                "prices": prices,
                "times": times
            }
            response["msg_type"] = "history"

        elif req_type == "forget":
            response["forget"] = 1
            response["msg_type"] = "forget"

        elif req_type == "buy":
            # Simulate a contract purchase
            response["buy"] = {
                "balance_after": 9900.00,
                "contract_id": random.randint(10000000, 99999999),
                "longcode": "Win payout if Volatility 100 Index is strictly higher than entry spot at 1 minute after contract start time.",
                "start_time": int(time.time()),
                "transaction_id": random.randint(100000000, 999999999),
                "purchase_time": int(time.time()),
                "buy_price": request.get("buy").get("price", 100),
                "payout": 200
            }
            response["msg_type"] = "buy"

        elif req_type == "portfolio":
            # Simulate portfolio data
            response["portfolio"] = {
                "contracts": [
                    {
                        "contract_id": random.randint(10000000, 99999999),
                        "longcode": "Win payout if Volatility 100 Index is strictly higher than entry spot at 1 minute after contract start time.",
                        "expiry_time": int(time.time()) + 3600,
                        "currency": "USD",
                        "buy_price": 100,
                        "entry_spot": 1050.25,
                        "current_spot": 1060.50,
                        "current_spot_display_value": "1060.50",
                        "current_spot_time": int(time.time()) - 10,
                        "profit": 95.50,
                        "profit_percentage": 95.5,
                        "status": "open",
                        "payout": 200,
                        "purchase_time": int(time.time()) - 300,
                        "symbol": "1HZ100V",
                        "contract_type": "CALL",
                        "underlying": "1HZ100V"
                    }
                ]
            }
            response["msg_type"] = "portfolio"

        else:
            # Generic response for unhandled request types
            response["msg_type"] = f"simulated_{req_type}"
            if req_type:
                response[req_type] = {"simulated": True, "message": "This is a simulated response"}

        # Add delay to simulate network latency
        await asyncio.sleep(random.uniform(0.1, 0.5))

        return response

    async def _message_handler(self):
        """Background task to handle incoming WebSocket messages."""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                try:
                    response = json.loads(message)
                    req_id = response.get('req_id')
                    msg_type = response.get('msg_type')

                    if req_id and req_id in self.pending_requests:
                        # Fulfill the pending request
                        future = self.pending_requests.pop(req_id)
                        future.set_result(response)
                    elif msg_type in ('tick', 'ohlc', 'candle', 'proposal_open_contract'):
                        # Handle subscription updates
                        subscription_id = response.get('subscription', {}).get('id')
                        if subscription_id and subscription_id in self.subscriptions:
                            callback = self.subscriptions[subscription_id]
                            # Call the callback with the response
                            try:
                                await callback(response)
                            except Exception as e:
                                logger.error(f"Error in subscription callback: {e}")
                    else:
                        # Handle subscription messages or other non-request responses
                        logger.debug(f"Received message without req_id: {msg_type}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message: {message}")
        except websockets.exceptions.ConnectionClosedError:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.exception(f"Error in message handler: {e}")

    async def _send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request to the Deriv API and wait for the response.

        Args:
            request_data: The request payload

        Returns:
            Dict: The API response
        """
        # For simulation mode, return simulated responses
        if self.simulation_mode:
            return await self._simulated_response(request_data)

        if not self.websocket:
            logger.error("Cannot send request: No websocket connection")
            return {"error": {"message": "No connection"}}

        # Generate a simple numeric request ID
        req_id = str(int(time.time() * 1000))  # Use millisecond timestamp
        request_data['req_id'] = req_id

        # Remove app_id from request data
        if 'app_id' in request_data:
            del request_data['app_id']

        # Create a future to wait for the response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[req_id] = future

        try:
            await self.websocket.send(json.dumps(request_data))
            # Wait for the response with a timeout
            response = await asyncio.wait_for(future, timeout=config.CONNECTION_TIMEOUT)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            logger.error(f"Request {req_id} timed out")
            return {"error": {"message": "Request timed out"}}
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            logger.error(f"Error sending request: {e}")
            return {"error": {"message": str(e)}}

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the API with exponential backoff.

        Returns:
            bool: True if reconnection is successful, False otherwise.
        """
        # In simulation mode, just reset the connection state
        if self.simulation_mode:
            logger.info("SIMULATION MODE: Simulating reconnection")
            self.is_connected = True
            self.connection_attempts = 0
            self.last_ping_time = time.time()
            return True

        self.connection_attempts += 1
        if self.connection_attempts >= config.MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Maximum reconnection attempts ({config.MAX_RECONNECT_ATTEMPTS}) reached")
            return False

        # Immediate reconnection without delay
        delay = 0.1

        logger.info(f"Attempting to reconnect in {delay:.1f} seconds (attempt {self.connection_attempts}/{config.MAX_RECONNECT_ATTEMPTS})")
        await asyncio.sleep(delay)

        # Close existing connection if any
        await self.disconnect()

        # Try alternative endpoints if previous attempts failed
        if self.connection_attempts > 1:
            alternate_endpoints = [
                "wss://ws.binaryws.com/websockets/v3",
                "wss://ws.derivapi.com/websockets/v3",
                "wss://52.53.244.116/websockets/v3"  # IP-based fallback
            ]
            self.endpoint = alternate_endpoints[self.connection_attempts % len(alternate_endpoints)]
            logger.info(f"Trying alternative endpoint: {self.endpoint}")

        # Attempt to reconnect
        return await self.connect()

    async def disconnect(self) -> None:
        """Disconnect from the Deriv API."""
        # In simulation mode, just reset the connection state
        if self.simulation_mode:
            logger.info("SIMULATION MODE: Simulating disconnection")
            self.is_connected = False
            return

        if self.websocket:
            try:
                logger.info("Disconnecting from Deriv API...")
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
                # Clear pending requests
                for req_id, future in self.pending_requests.items():
                    if not future.done():
                        future.set_exception(Exception("Connection closed"))
                self.pending_requests.clear()
                # Clear subscriptions
                self.subscriptions.clear()

    async def ping(self) -> bool:
        """
        Send a ping to check if the connection is still alive.

        Returns:
            bool: True if connection is active, False otherwise.
        """
        # In simulation mode, always return success
        if self.simulation_mode:
            self.last_ping_time = time.time()
            return True

        if not self.websocket:
            return False

        try:
            # Use a simple ping request
            response = await self._send_request({"ping": 1})
            self.last_ping_time = time.time()

            # If we got a response, the connection is alive
            if response.get('ping') == 'pong':
                return True
            return False
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            self.is_connected = False
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get information about the current account.

        Returns:
            Dict: Account information or empty dict if not connected.
        """
        # For simulation mode, return the simulated account info
        if self.simulation_mode:
            if not self.is_connected:
                logger.warning("Cannot get account info: Not connected (simulation mode)")
                return {}
            return self.account_info

        if not self.is_connected or not self.websocket:
            logger.warning("Cannot get account info: Not connected")
            return {}

        try:
            # Use cached account info if available
            if self.account_info:
                return self.account_info

            # Otherwise fetch it
            response = await self._send_request({
                "authorize": self.api_token,
                "app_id": self.app_id
            })
            self.account_info = response
            return response
        except Exception as e:
            logger.error(f"Failed to get account information: {e}")
            return {}

    async def send_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send a custom request to the Deriv API.

        Args:
            request_data (Dict): The request payload to send.

        Returns:
            Dict: The API response or None if the request failed.
        """
        # Handle simulation mode
        if self.simulation_mode:
            if not self.is_connected:
                logger.warning("Cannot send request: Not connected (simulation mode)")
                return None
            return await self._simulated_response(request_data)

        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send request: Not connected")
            return None

        try:
            response = await self._send_request(request_data)
            return response
        except Exception as e:
            logger.error(f"Request failed: {e}")
            # Check if we should attempt to reconnect
            if isinstance(e, (websockets.exceptions.ConnectionClosedError,
                               websockets.exceptions.ConnectionClosedOK)):
                self.is_connected = False
                logger.info("Connection lost. Will attempt to reconnect on next operation.")
            return None

    async def subscribe(self, request: Dict[str, Any], callback) -> Optional[str]:
        """
        Subscribe to a live feed from the API.

        Args:
            request: The subscription request
            callback: Async function to call with each update

        Returns:
            str: Subscription ID if successful, None otherwise
        """
        # For simulation mode, set up a background task to generate simulated updates
        if self.simulation_mode:
            if not self.is_connected:
                logger.warning("Cannot subscribe: Not connected (simulation mode)")
                return None

            # Generate a subscription ID
            sub_id = str(uuid.uuid4())

            # Store callback
            self.subscriptions[sub_id] = callback

            # Set up a background task to send simulated updates
            req_type = next((k for k in request.keys() if k not in ('req_id', 'app_id')), None)
            asyncio.create_task(self._simulate_subscription(req_type, request, sub_id, callback))

            return sub_id

        # Regular API subscription
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot subscribe: Not connected")
            return None

        try:
            # Send the subscription request
            response = await self._send_request(request)

            # Check for errors
            if 'error' in response:
                error_msg = extract_error_message(response)
                logger.error(f"Subscription failed: {error_msg}")
                return None

            # Get the subscription ID
            subscription = response.get('subscription', {})
            sub_id = subscription.get('id')

            if not sub_id:
                logger.error("Subscription failed: No subscription ID returned")
                return None

            # Store the callback with the subscription ID
            self.subscriptions[sub_id] = callback

            return sub_id
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return None

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a feed.

        Args:
            subscription_id: The subscription ID to cancel

        Returns:
            bool: True if successful, False otherwise
        """
        # For simulation mode
        if self.simulation_mode:
            if subscription_id in self.subscriptions:
                del self.subscriptions[subscription_id]
                logger.info(f"SIMULATION MODE: Unsubscribed from {subscription_id}")
                return True
            return False

        # Regular API unsubscription
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot unsubscribe: Not connected")
            return False

        try:
            # Send a forget request
            response = await self._send_request({
                "forget": subscription_id
            })

            # Check the response
            if response.get('forget') == 1:
                # Remove the subscription callback
                if subscription_id in self.subscriptions:
                    del self.subscriptions[subscription_id]
                return True
            else:
                error_msg = extract_error_message(response)
                logger.error(f"Unsubscribe failed: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
            return False

    async def _simulate_subscription(self, req_type: str, request: Dict[str, Any], sub_id: str, callback):
        """Generate simulated subscription updates."""
        try:
            # Continue until unsubscribed or disconnected
            while self.is_connected and sub_id in self.subscriptions:
                # Generate a simulated update based on the subscription type
                response = await self._simulated_response(request)

                # Add subscription ID to the response
                response['subscription'] = {'id': sub_id}

                # Call the callback with the simulated data
                await callback(response)

                # Wait before sending the next update (more frequent for ticks, less for others)
                if req_type == 'ticks':
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                else:
                    await asyncio.sleep(random.uniform(1.0, 3.0))

        except asyncio.CancelledError:
            logger.debug(f"Simulated subscription {sub_id} cancelled")
        except Exception as e:
            logger.error(f"Error in simulated subscription: {e}")
        finally:
            # Remove subscription if still present
            if sub_id in self.subscriptions:
                del self.subscriptions[sub_id]

    async def switch_account(self, use_demo: bool) -> bool:
        """
        Switch between demo and real accounts.

        Args:
            use_demo (bool): Whether to use the demo account.

        Returns:
            bool: True if the switch was successful, False otherwise.
        """
        # If we're already using the requested account type, do nothing
        if self.is_demo == use_demo:
            logger.info(f"Already using {'demo' if use_demo else 'real'} account")
            return True

        logger.info(f"Switching to {'demo' if use_demo else 'real'} account")

        # Disconnect from current account
        await self.disconnect()

        # Update account type
        self.is_demo = use_demo
        self.api_token = config.DERIV_API_TOKEN_DEMO if use_demo else config.DERIV_API_TOKEN_REAL
        self.endpoint = config.DERIV_DEMO_WSS_ENDPOINT if use_demo else config.DERIV_WSS_ENDPOINT

        # Update simulation mode status
        self.simulation_mode = self._is_placeholder_token(self.api_token) and config.ENABLE_SIMULATION

        # Connect to new account
        return await self.connect()

    # Convenience methods for common API operations

    async def get_ticks(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest tick data for a symbol.

        Args:
            symbol: The symbol to get tick data for (e.g., "R_100")

        Returns:
            Dict: The tick data or None if the request failed
        """
        return await self.send_request({
            "ticks": symbol
        })

    async def get_ticks_history(self, symbol: str, count: int = 10, end: str = "latest") -> Optional[Dict[str, Any]]:
        """
        Get historical tick data for a symbol.

        Args:
            symbol: The symbol to get data for
            count: Number of ticks to get
            end: End time of the history data, "latest" for current time

        Returns:
            Dict: The historical data or None if the request failed
        """
        return await self.send_request({
            "ticks_history": symbol,
            "count": count,
            "end": end,
            "style": "ticks"
        })

    async def get_candles(self, symbol: str, count: int = 10, granularity: int = 60) -> Optional[Dict[str, Any]]:
        """
        Get OHLC candle data for a symbol.

        Args:
            symbol: The symbol to get data for
            count: Number of candles to get
            granularity: Candle interval in seconds (60, 120, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 86400)

        Returns:
            Dict: The candle data or None if the request failed
        """
        return await self.send_request({
            "ticks_history": symbol,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": granularity
        })

    async def get_proposal(self, contract_type: str, symbol: str, amount: float, duration: int, duration_unit: str) -> Optional[Dict[str, Any]]:
        """
        Get a price proposal for a contract.

        Args:
            contract_type: Type of contract (e.g., "CALL", "PUT")
            symbol: The symbol to trade
            amount: Stake amount
            duration: Contract duration
            duration_unit: Duration unit (s, m, h, d)

        Returns:
            Dict: The proposal data or None if the request failed
        """
        return await self.send_request({
            "proposal": 1,
            "amount": amount,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": duration,
            "duration_unit": duration_unit,
            "symbol": symbol
        })

    async def buy_contract(self, proposal_id: str, price: float) -> Optional[Dict[str, Any]]:
        """
        Buy a contract using a proposal.

        Args:
            proposal_id: ID of the proposal to buy
            price: Price to pay

        Returns:
            Dict: The purchase result or None if the request failed
        """
        return await self.send_request({
            "buy": proposal_id,
            "price": price
        })

    async def get_portfolio(self) -> Optional[Dict[str, Any]]:
        """
        Get the current portfolio of open contracts.

        Returns:
            Dict: The portfolio data or None if the request failed
        """
        return await self.send_request({
            "portfolio": 1
        })

    async def subscribe_ticks(self, symbol: str, callback) -> Optional[str]:
        """
        Subscribe to tick updates for a symbol.

        Args:
            symbol: The symbol to subscribe to
            callback: Async function to call with each tick update

        Returns:
            str: Subscription ID if successful, None otherwise
        """
        return await self.subscribe({
            "ticks": symbol
        }, callback)

    async def subscribe_candles(self, symbol: str, granularity: int, callback) -> Optional[str]:
        """
        Subscribe to candle updates for a symbol.

        Args:
            symbol: The symbol to subscribe to
            granularity: Candle interval in seconds
            callback: Async function to call with each candle update

        Returns:
            str: Subscription ID if successful, None otherwise
        """
        return await self.subscribe({
            "ticks_history": symbol,
            "style": "candles",
            "granularity": granularity,
            "subscribe": 1
        }, callback)

    async def subscribe_proposal(self, contract_params: Dict[str, Any], callback) -> Optional[str]:
        """
        Subscribe to proposal updates.

        Args:
            contract_params: Contract parameters
            callback: Async function to call with each proposal update

        Returns:
            str:str: Subscription ID if successful, None otherwise
        """
        request = {
            "proposal": 1,
            "subscribe": 1,
            **contract_params
        }
        return await self.subscribe(request, callback)

    async def subscribe_transaction(self, callback) -> Optional[str]:
        """
        Subscribe to transaction updates.

        Args:
            callback: Async function to call with each transaction update

        Returns:
            str: Subscription ID if successful, None otherwise
        """
        return await self.subscribe({
            "transaction": 1,
            "subscribe": 1
        }, callback)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Perform a comprehensive connection test and return detailed results.

        This method tests various aspects of the API connection including:
        - Authentication
        - Account information retrieval
        - Market data access
        - Ping functionality
        - Reconnection capability

        Returns:
            Dict: Test results with details on each test
        """
        results = {
            "connection": {"status": "not_tested", "details": ""},
            "authentication": {"status": "not_tested", "details": ""},
            "account_info": {"status": "not_tested", "details": ""},
            "market_data": {"status": "not_tested", "details": ""},
            "ping": {"status": "not_tested", "details": ""},
            "reconnection": {"status": "not_tested", "details": ""},
            "overall": {"status": "not_tested", "details": ""}
        }

        # Test basic connection and authentication
        try:
            logger.info("Testing API connection...")
            results["connection"]["status"] = "testing"

            # Check if already connected or connect
            if not self.is_connected:
                connected = await self.connect()
                if not connected:
                    results["connection"]["status"] = "failed"
                    results["connection"]["details"] = "Could not establish connection to API"
                    results["overall"]["status"] = "failed"
                    results["overall"]["details"] = "Connection failed"
                    return results

            results["connection"]["status"] = "passed"
            results["connection"]["details"] = "Successfully connected to API"
            results["authentication"]["status"] = "passed"
            results["authentication"]["details"] = "Authentication successful"

            # Test account info retrieval
            logger.info("Testing account information retrieval...")
            results["account_info"]["status"] = "testing"
            account_info = await self.get_account_info()

            if not account_info or 'authorize' not in account_info:
                results["account_info"]["status"] = "failed"
                results["account_info"]["details"] = "Failed to retrieve account information"
            else:
                auth_info = account_info['authorize']
                account_id = auth_info.get('loginid', 'Unknown')
                currency = auth_info.get('currency', 'Unknown')

                results["account_info"]["status"] = "passed"
                results["account_info"]["details"] = f"Retrieved info for account {account_id} ({currency})"

            # Test market data access
            logger.info("Testing market data access...")
            results["market_data"]["status"] = "testing"
            symbol = "R_100"
            tick_data = await self.get_ticks(symbol)

            if not tick_data or 'tick' not in tick_data:
                results["market_data"]["status"] = "failed"
                results["market_data"]["details"] = f"Failed to retrieve tick data for {symbol}"
            else:
                tick = tick_data['tick']
                price = tick.get('quote', 'N/A')

                results["market_data"]["status"] = "passed"
                results["market_data"]["details"] = f"Retrieved current {symbol} price: {price}"

            # Test ping functionality
            logger.info("Testing ping functionality...")
            results["ping"]["status"] = "testing"
            ping_result = await self.ping()

            if not ping_result:
                results["ping"]["status"] = "failed"
                results["ping"]["details"] = "Ping test failed, connection might be unreliable"
            else:
                results["ping"]["status"] = "passed"
                results["ping"]["details"] = "Ping test successful, connection is stable"

            # Test reconnection
            logger.info("Testing reconnection capability...")
            results["reconnection"]["status"] = "testing"

            # Disconnect first
            await self.disconnect()
            if self.is_connected:
                results["reconnection"]["status"] = "failed"
                results["reconnection"]["details"] = "Failed to disconnect for reconnection test"
            else:
                # Try to reconnect
                reconnected = await self.reconnect()

                if not reconnected:
                    results["reconnection"]["status"] = "failed"
                    results["reconnection"]["details"] = "Failed to reconnect after disconnection"
                else:
                    results["reconnection"]["status"] = "passed"
                    results["reconnection"]["details"] = "Successfully reconnected after disconnection"

            # Determine overall status
            all_passed = all(item["status"] == "passed" for item in results.values() if item != results["overall"])

            if all_passed:
                results["overall"]["status"] = "passed"
                results["overall"]["details"] = "All tests passed successfully"
            else:
                results["overall"]["status"] = "partial"
                failed_tests = [k for k, v in results.items() if v["status"] == "failed" and k != "overall"]
                results["overall"]["details"] = f"Some tests failed: {', '.join(failed_tests)}"

            return results

        except Exception as e:
            logger.exception(f"Error during connection testing: {e}")
            results["overall"]["status"] = "error"
            results["overall"]["details"] = f"Exception occurred: {str(e)}"
            return results

    def get_token_diagnostic(self, token: str) -> str:
        """
        Generate diagnostic information about a token without exposing its value.

        Args:
            token: The token to diagnose

        Returns:
            str: Diagnostic information about the token
        """
        if not token:
            return "Token is empty"

        if token.startswith("placeholder_"):
            return "Using placeholder token (simulation mode recommended)"

        length = len(token)
        alpha_count = sum(c.isalpha() for c in token)
        digit_count = sum(c.isdigit() for c in token)
        special_count = length - alpha_count - digit_count

        # Check if token matches expected format (based on observations)
        matches_expected_format = bool(re.match(r'^[A-Za-z0-9]{10,30}$', token))
        format_status = "Valid format" if matches_expected_format else "Unexpected format"

        diagnostic = (
            f"Token length: {length} chars, "
            f"Composition: {alpha_count} letters, {digit_count} digits, {special_count} special chars, "
            f"Format: {format_status}"
        )

        # Show first and last 3 characters with *** in between
        if length > 8:
            masked_token = f"{token[:3]}{'*' * (length-6)}{token[-3:]}"
        else:
            masked_token = "***"

        # Add connection troubleshooting tips
        if not matches_expected_format:
            diagnostic += "\nTip: Deriv tokens are typically alphanumeric strings around 15 characters"
            
        return f"{diagnostic}, Token preview: {masked_token}"

    async def _ping_handler(self):
        """Keep connection alive with ping/pong following Deriv documentation."""
        while self.is_connected:
            try:
                # Send ping every 30 seconds as recommended by Deriv
                await asyncio.sleep(config.PING_INTERVAL)
                
                if not self.is_connected:
                    break

                ping_response = await self._send_request({"ping": 1})
                
                if not ping_response or ping_response.get('ping') != 'pong':
                    logger.warning("Invalid ping response, attempting reconnection...")
                    self.is_connected = False
                    asyncio.create_task(self.reconnect())
                    break
                
                self.last_ping_time = time.time()
                
            except Exception as e:
                logger.error(f"Ping error: {e}")
                self.is_connected = False
                asyncio.create_task(self.reconnect())
                break

    async def get_available_contracts(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get available contract types for a symbol.
        
        Args:
            symbol: The trading symbol to get contracts for

        Returns:
            Dict: Available contract types and their parameters or None if request failed
        """
        return await self.send_request({
            "contracts_for": symbol,
            "currency": "USD",
            "landing_company": "maltainvest",
            "product_type": "basic"
        })
