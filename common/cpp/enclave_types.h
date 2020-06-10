/* Copyright 2020 Intel Corporation
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

#pragma once

/** Avalon worker enclave Type (singleton, KME, WPE) */
enum EnclaveType {
    /** SINGLETON_ENCLAVE does both Key management and workload processing */
    SINGLETON_ENCLAVE = 1,
    /** KME_ENCLAVE is responsible for secure key management */
    KME_ENCLAVE = 2,
    /** WPE_ENCLAVE is responsible for workload management */
    WPE_ENCLAVE = 3
};

