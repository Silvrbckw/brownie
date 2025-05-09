import re
from typing import Callable, Dict, List, Optional

from web3 import Web3

from brownie.network.middlewares import BrownieMiddlewareABC


class HardhatMiddleWare(BrownieMiddlewareABC):
    @classmethod
    def get_layer(cls, w3: Web3, network_type: str) -> Optional[int]:
        return -100 if w3.clientVersion.lower().startswith("hardhat") else None

    def process_request(self, make_request: Callable, method: str, params: List) -> Dict:
        result = make_request(method, params)

        # modify Hardhat transaction error to mimick the format that Ganache uses
        if (
            method in {"eth_call", "eth_sendTransaction", "eth_sendRawTransaction"}
            and "error" in result
        ):
            message = result["error"]["message"]
            if message.startswith("Error: VM Exception") or message.startswith(
                "Error: Transaction reverted"
            ):
                txid = "0x" if method == "eth_call" else result["error"]["data"]["txHash"]
                data: Dict = {}
                result["error"]["data"] = {txid: data}
                message = message.split(": ", maxsplit=1)[-1]
                if message == "Transaction reverted without a reason":
                    data.update({"error": "revert", "reason": None})
                elif message.startswith("revert"):
                    data.update({"error": "revert", "reason": message[7:]})
                elif "reverted with reason string '" in message:
                    data.update(error="revert", reason=re.findall(".*?'(.*)'$", message)[0])
                else:
                    data["error"] = message
        return result
