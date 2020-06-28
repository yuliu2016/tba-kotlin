import json

swagger_file = open("api_v3.json")
json_data = swagger_file.read()
swagger_file.close()

data = json.loads(json_data)

api_version = data["info"]["version"]
paths = data["paths"]
model_schemas = data["components"]["schemas"]

header = """@file:Suppress("unused", "SpellCheckingInspection", "KDocUnresolvedReference", "UNUSED_VARIABLE", "DuplicatedCode")

package kb.plugin.thebluealliance.api

import org.json.JSONObject"""

function_template = """
/**
 * {description}
 */
fun TBA.{operation_id}({params}): {kotlin_type} = {func_name}("{templated_path}"){body}"""

request_parameter_types = {
    "page_num": "Int",
    "year": "Int",
    "media_tag": "String",
    "team_key": "String",
    "event_key": "String",
    "match_key": "String",
    "district_key": "String"
}

def convert_to_kotlin_case(underscore_case):
    split = underscore_case.split("_")
    return "".join(word[0].capitalize() + word[1:] for word in split)


def function_for_api_path(path_name, path_def):
    get_request_definition = path_def["get"]
    operation_id = get_request_definition["operationId"]
    description = get_request_definition["description"]
    params = get_request_definition["parameters"]
    actual_params = []

    for i in range(len(params)):
        param = params[i]
        if "$ref" in param:
            param_name = params[i]["$ref"].split("/")[-1]
            if param_name != "If-Modified-Since":
                actual_params.append(param_name)
        else:
            actual_params.append(param["name"]) #FIXME

    get_response_schema = get_request_definition["responses"]["200"]["content"]["application/json"]["schema"]
    templated_path = path_name

    if len(actual_params) == 0:
        params_string = ""
    else:
        pdef = [x + ": " + request_parameter_types[x] for x in actual_params]
        params_string = "\n    " + ",\n    ".join(pdef) + "\n"
        for param in actual_params:
            templated_path = templated_path.replace("{" + param + "}", "$" + param)

    if "$ref" in get_response_schema:
        func_name = "get"
        referenced_definition = get_response_schema["$ref"].split("/")[-1]
        clz = convert_to_kotlin_case(referenced_definition)
        kotlin_type = clz
        body = f".to{clz}()"
    elif get_response_schema["type"] == "array":
        it = get_response_schema["items"]
        func_name = "getArray"
        if "$ref" in it:
            referenced_definition = it["$ref"].split("/")[-1]
            clz = convert_to_kotlin_case(referenced_definition)
            kotlin_type = "List<" + clz + ">"
            body = f".map {{ (it as JSONObject).to{clz}() }}"
        elif it["type"] == "string":
            kotlin_type = "List<String>"
            body = ".map { it as String }"
        elif it["type"] == "integer":
            kotlin_type = "List<Int>"
            body = ".map { it as Int }"
        elif it["type"] == "object":
            kotlin_type = "List<JSONObject>"
            body = ".map { it as JSONObject }"
        else:
            raise TypeError()

    elif get_response_schema["type"] == "object":
        func_name = "get"
        referenced_definition = get_response_schema["additionalProperties"]["$ref"].split("/")[-1]
        clz = convert_to_kotlin_case(referenced_definition)
        kotlin_type = "Map<String, " + clz + "?>"
        body = f".mapValues {{ (it as JSONObject?)!!.to{clz}() }}"

    else:
        raise TypeError()

    return function_template.format(
        description=description, operation_id=operation_id, params=params_string,
        kotlin_type=kotlin_type, templated_path=templated_path, body=body, func_name=func_name)


with open("Paths.kt", mode="w") as f:
    print("// The Blue Alliance API Version", api_version, "\n", file=f)
    print(header, file=f)
    for path_key, path_definition in paths.items():
        print(function_for_api_path(path_key, path_definition), file=f)
