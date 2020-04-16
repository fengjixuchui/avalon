# Copyright 2020 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import json
import random
import asyncio
import logging
import argparse
from urllib.parse import urlparse
from avalon_sdk.worker.worker_details import WorkerType, WorkerStatus
import avalon_sdk.worker.worker_details as worker_details
from avalon_sdk.work_order.work_order_params import WorkOrderParams

from avalon_sdk.connector.blockchains.ethereum.ethereum_work_order \
    import EthereumWorkOrderProxyImpl
from avalon_sdk.connector.blockchains.ethereum.ethereum_worker_registry \
    import EthereumWorkerRegistryImpl
from avalon_sdk.connector.blockchains.ethereum.ethereum_wrapper \
    import EthereumWrapper
from avalon_sdk.connector.blockchains.ethereum.ethereum_listener \
    import BlockchainInterface, EventProcessor
from avalon_sdk.connector.direct.jrpc.jrpc_worker_registry \
    import JRPCWorkerRegistryImpl
from avalon_sdk.connector.direct.jrpc.jrpc_work_order \
    import JRPCWorkOrderImpl


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Return codes
SUCCESS = 0
ERROR = 1


class EthereumConnector:

    """
    This class is the bridge between the Ethereum blockchain and the Avalon
    core. It listens for events generated by the Ethereum blockchain.
    It handles event data corresponding to the event (eg: workOrderSubmitted
    and submits requests to Avalon on behalf of the client. The service also
    invokes smart contract APIs (eg: workOrderComplete).
    """

    def __init__(self, config):

        self._config = config
        self._eth_client = EthereumWrapper(config)
        tcf_home = os.environ.get("TCF_HOME", "../../")

        worker_reg_contract_file = tcf_home + "/" + \
            config["ethereum"]["worker_registry_contract_file"]
        worker_reg_contract_address = \
            config["ethereum"]["worker_registry_contract_address"]
        self._worker_reg_contract_instance,\
            self._worker_reg_contract_instance_evt = self._eth_client\
            .get_contract_instance(
                worker_reg_contract_file, worker_reg_contract_address)

        self._worker_registry = EthereumWorkerRegistryImpl(config)

        work_order_contract_file = tcf_home + "/" + \
            config["ethereum"]["work_order_contract_file"]
        work_order_contract_address = \
            config["ethereum"]["work_order_contract_address"]
        self._work_order_contract_instance,\
            self._work_order_contract_instance_evt = self._eth_client\
            .get_contract_instance(
                work_order_contract_file, work_order_contract_address)

        self._work_order_proxy = EthereumWorkOrderProxyImpl(config)

    def _lookup_workers_in_kv_storage(self, worker_registry):
        """
        This function retrieves the worker ids from shared kv using
        worker_lookup direct API.
        Returns list of worker id
        """
        jrpc_req_id = random.randint(0, 100000)

        worker_lookup_result = worker_registry.worker_lookup(
            worker_type=WorkerType.TEE_SGX, id=jrpc_req_id
        )
        logging.info("\nWorker lookup response from kv storage : {}\n".format(
            json.dumps(worker_lookup_result, indent=4)
        ))
        if "result" in worker_lookup_result and \
                "ids" in worker_lookup_result["result"].keys():
            if worker_lookup_result["result"]["totalCount"] != 0:
                return worker_lookup_result["result"]["ids"]
            else:
                logging.error("No workers found in kv storage")
        else:
            logging.error("Failed to lookup worker in kv storage")
        return []

    def _retrieve_worker_details_from_kv_storage(self, worker_registry,
                                                 worker_id):
        # Retrieve worker details
        jrpc_req_id = random.randint(0, 100000)
        worker_info = worker_registry.worker_retrieve(worker_id, jrpc_req_id)
        logging.info("Worker retrieve response from kv storage: {}"
                     .format(json.dumps(worker_info, indent=4)))

        if "error" in worker_info:
            logging.error("Unable to retrieve worker details from kv storage")
        return worker_info["result"]

    def _add_update_worker_to_chain(self, wids_onchain, wids_kv,
                                    jrpc_worker_registry):
        """
        This function adds/updates a worker in the Ethereum blockchain
        """

        for wid in wids_kv:
            worker_info = self._retrieve_worker_details_from_kv_storage(
                jrpc_worker_registry, wid)
            worker_id = wid
            worker_type = WorkerType(worker_info["workerType"])
            org_id = worker_info["organizationId"]
            app_type_id = worker_info["applicationTypeId"]
            details = json.dumps(worker_info["details"])

            result = None
            if wid in wids_onchain:
                logging.info("Updating worker {} on ethereum blockchain"
                             .format(wid))
                result = self._worker_registry.worker_update(
                    worker_id, details)
            else:
                logging.info("Adding new worker {} to ethereum blockchain"
                             .format(wid))
                result = self._worker_registry.worker_register(
                    worker_id, worker_type, org_id, [app_type_id], details
                )
            if result is None:
                logging.error("Error while adding/updating worker to ethereum"
                              + " blockchain")

        for wid in wids_onchain:
            # Mark all stale workers on blockchain as decommissioned
            if wid not in wids_kv:
                worker_id = wid
                worker = self._worker_registry\
                    .worker_retrieve(wid, random.randint(0, 100000))
                worker_status_onchain = worker["result"]["status"]
                # If worker is not already decommissoined, mark it decommission
                # as it is no longer available in the kv storage
                if worker_status_onchain != WorkerStatus.DECOMMISSIONED.value:
                    self._worker_registry.worker_set_status(
                        worker_id, WorkerStatus.DECOMMISSIONED)
                    logging.info("Marked worker "+wid+" as decommissioned on"
                                 + " ethereum blockchain")

    def _lookup_workers_onchain(self):
        """
        Lookup all workers on chain to sync up with kv storage
        """
        jrpc_req_id = random.randint(0, 100000)
        # TODO: Remove hardcoding and pass wild characters instead
        worker_lookup_result = self._worker_registry.worker_lookup(
            WorkerType.TEE_SGX,
            self._config["WorkerConfig"]["OrganizationId"],
            self._config["WorkerConfig"]["ApplicationTypeId"],
            jrpc_req_id
        )
        logging.info("Worker lookup response from blockchain: {}\n".format(
            json.dumps(worker_lookup_result, indent=4)
        ))
        if "result" in worker_lookup_result and \
                "ids" in worker_lookup_result["result"].keys():
            if worker_lookup_result["result"]["totalCount"] != 0:
                return worker_lookup_result["result"]["ids"]
            else:
                logging.error("No workers found in ethereum blockchain")
        else:
            logging.error("Failed to lookup worker in ethereum blockchain")
        return []

    def _submit_work_order_and_get_result(self, work_order_id, worker_id,
                                          requester_id, work_order_params):
        """
        This function submits work order using work_order_submit direct API
        """
        work_order_impl = JRPCWorkOrderImpl(self._config)
        logging.info("About to submit work order to kv storage")
        response = work_order_impl\
            .work_order_submit(work_order_id, worker_id, requester_id,
                               work_order_params, id=random.randint(0, 100000))
        logging.info("Work order submit response : {}".format(
            json.dumps(response, indent=4)))

        work_order_result = work_order_impl\
            .work_order_get_result(work_order_id,
                                   id=random.randint(0, 100000))

        logging.info("Work order get result : {} "
                     .format(json.dumps(work_order_result, indent=4)))

        return work_order_result

    def _add_work_order_result_to_chain(self, work_order_id, response):
        """
        This function adds a work order result to the Ethereum blockchain
        """
        result = self._work_order_proxy.work_order_complete(
            work_order_id, json.dumps(response))
        if result == SUCCESS:
            logging.info("Successfully added work order result to blockchain")
        else:
            logging.error("Error adding work order result to blockchain")
        return result

    def handleEvent(self, event, account, contract):
        """
        The function retrieves pertinent information from the event received
        and makes request to listener using Direct API and writes back result
        to the blockchain
        """

        work_order_request = json.loads(event["args"]["workOrderRequest"])

        work_order_id = work_order_request["workOrderId"]
        worker_id = work_order_request["workerId"]
        requester_id = work_order_request["requesterId"]
        work_order_params = event["args"]["workOrderRequest"]
        logging.info("Received event from blockchain")
        response = self\
            ._submit_work_order_and_get_result(work_order_id, worker_id,
                                               requester_id,
                                               work_order_params)
        self._add_work_order_result_to_chain(work_order_id, response)

    def start(self):
        logging.info("Ethereum Connector service started")

        # Fetch first worker details from shared KV (via direct API)
        # and add the worker to block chain.
        # TODO: Fetch all workers from shared KV and block chain
        # and do 2-way sync.
        jrpc_worker_registry = JRPCWorkerRegistryImpl(self._config)
        worker_ids_onchain = self._lookup_workers_onchain()
        worker_ids_kv = self._lookup_workers_in_kv_storage(
            jrpc_worker_registry)

        self._add_update_worker_to_chain(worker_ids_onchain, worker_ids_kv,
                                         jrpc_worker_registry)

        # Start an event listener that listens for events from the proxy
        # blockchain, extracts request payload from there and make a request
        # to avalon-listener

        w3 = BlockchainInterface(self._config)

        contract = self._work_order_contract_instance_evt
        # Listening only for workOrderSubmitted event now
        listener = w3.newListener(contract, "workOrderSubmitted")

        try:
            daemon = EventProcessor(self._config)
            asyncio.get_event_loop().run_until_complete(daemon.start(
                listener,
                self.handleEvent,
                account=None,
                contract=contract,
            ))
        except KeyboardInterrupt:
            asyncio.get_event_loop().run_until_complete(daemon.stop())
