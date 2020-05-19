/* Copyright 2018 Intel Corporation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "enclave_u.h"

#include "tcf_error.h"
#include "error.h"
#include "avalon_sgx_error.h"
#include "log.h"
#include "types.h"

#include "enclave.h"
#include "base.h"
#include "work_order.h"

tcf_err_t WorkOrderHandlerBase::GetSerializedResponse(
    const uint32_t inResponseIdentifier,
    const size_t inSerializedResponseSize,
    Base64EncodedString& outSerializedResponse,
    int enclaveIndex) {
    tcf_err_t result = TCF_SUCCESS;

    try {
        ByteArray serialized_response(inSerializedResponseSize);

        // xxxxx Call the enclave

        // Get the enclave id for passing into the ecall
        sgx_enclave_id_t enclaveid = g_Enclave[enclaveIndex].GetEnclaveId();

        tcf_err_t presult = TCF_SUCCESS;
        sgx_status_t sresult =

            g_Enclave[enclaveIndex].CallSgx(
                [
                    enclaveid,
                    &presult,
                    &serialized_response
                ]
                () {
                    sgx_status_t sresult_inner = ecall_GetSerializedResponse(
                        enclaveid,
                        &presult,
                        serialized_response.data(),
                        serialized_response.size());
                    return tcf::error::ConvertErrorStatus(sresult_inner, presult);
                });
        tcf::error::ThrowSgxError(sresult,
            "Intel SGX enclave call failed (GetSerializedResponse)");
        g_Enclave[enclaveIndex].ThrowTCFError(presult);

        outSerializedResponse = ByteArrayToBase64EncodedString(serialized_response);
    } catch (tcf::error::Error& e) {
        tcf::enclave_api::base::SetLastError(e.what());
        result = e.error_code();
    } catch (std::exception& e) {
        tcf::enclave_api::base::SetLastError(e.what());
        result = TCF_ERR_UNKNOWN;
    } catch (...) {
        tcf::enclave_api::base::SetLastError("Unexpected exception");
        result = TCF_ERR_UNKNOWN;
    }

    return result;
}
