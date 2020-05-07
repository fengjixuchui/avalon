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

/**
 * @file
 * Avalon string utilities,
 * including base 64, hex, byte array, and string array conversion.
 */

#include <algorithm>
#include <string>
#include <vector>

#include "types.h"
#include "base64.h"
#include "hex_string.h"


/**
 * Simple conversion from ByteArray to std::string
 */
std::string ByteArrayToString(const ByteArray& inArray) {
    std::string outString;
    std::transform(inArray.begin(), inArray.end(),
                   std::back_inserter(outString),
                   [](unsigned char c) -> char { return (char)c; });

    return outString;
}


/**
 * Conversion from ByteArray to StringArray.
 */
StringArray ByteArrayToStringArray(const ByteArray& inArray) {
    StringArray sarray(0);
    std::transform(inArray.begin(), inArray.end(), std::back_inserter(sarray),
                   [](unsigned char c) -> char { return (char)c; });
    return sarray;
}


/**
 * Simple conversion from ByteArray to Base64EncodedString.
 */
Base64EncodedString ByteArrayToBase64EncodedString(const ByteArray& buf) {
    return base64_encode(buf);
}  // ByteArrayToBase64EncodedString


/**
 * Simple conversion from Base64EncodedString to ByteArray.
 */
ByteArray Base64EncodedStringToByteArray(const Base64EncodedString& encoded) {
    return base64_decode(encoded);
}  // Base64EncodedStringToByteArray


/**
 * Simple conversion from ByteArray to HexEncodedString.
 */
HexEncodedString ByteArrayToHexEncodedString(const ByteArray& buf) {
    return tcf::BinaryToHexString(buf);
}  // ByteArrayToHexEncodedString


/**
 * Simple conversion from HexEncodedString to ByteArray.
 * Throws ValueError.
 */
ByteArray HexEncodedStringToByteArray(const HexEncodedString& encoded) {
    return tcf::HexStringToBinary(encoded);
}  // HexEncodedStringToByteArray
