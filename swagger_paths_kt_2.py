import json

swagger_file = open("api_v3.json")
json_data = swagger_file.read()
swagger_file.close()

data = json.loads(json_data)

api_version = data["info"]["version"]
paths = data["paths"]
definitions = data["components"]["schemas"]

header = """@file:Suppress("unused", "SpellCheckingInspection", "KDocUnresolvedReference", "UNUSED_VARIABLE", "DuplicatedCode")

package kb.plugin.thebluealliance.api

import com.beust.klaxon.JsonObject"""

function_template = """
/**
 * {des}
 */
fun TBA.{op_id}({params}): {typing} {{
    val response = {fname}("{k}")
    {body}
}}"""

request_parameter_types = {
    "page_num": "Int",
    "year": "Int",
    "media_tag": "String",
    "team_key": "String",
    "event_key": "String",
    "match_key": "String",
    "district_key": "String"
}

scoped_function_template = """{name}.obj("{p}")?.let {{ {p} ->
{i8}{ldef}
{i4}}}"""

data_get_call_template = """{name}.{typ}("{p}")"""

alliance_template = """Alliances(
{i8}blue = {name}.obj("blue")?.let {{ alliance ->
{i12}{ldef}
{i8}}},
{i8}red = {name}.obj("blue")?.let {{ alliance ->
{i12}{ldef}
{i8}}}
)"""


def convert_to_kotlin_case(underscore_case):
    split = underscore_case.split("_")
    return "".join(word[0].capitalize() + word[1:] for word in split)


def function_code_for_definition(referenced_definition, name, indent):
    indent4 = indent + 4
    indent8 = indent + 8

    def_content = definitions[referenced_definition]

    if "properties" in def_content:
        properties = def_content["properties"]
    else:
        properties = {}

    kotlin_name = convert_to_kotlin_case(referenced_definition)

    return_string = kotlin_name + "(\n"

    parameter_list = ["raw = " + name]

    for property_name, property_def in properties.items():

        # reserved words
        if property_name == "in":
            fixed_param_name = "_in"
        else:
            fixed_param_name = property_name

        kotlin_param_data = ""#fixed_param_name + " = "

        if "$ref" in property_def:
            referenced_definition = property_def["$ref"].split("/")[-1]

            kotlin_param_data += scoped_function_template.format(
                name=name, p=property_name, i8=" " * indent8, i4=" " * indent4,
                ldef=function_code_for_definition(referenced_definition, property_name, indent8))

        elif property_name == "alliances":
            referenced_definition = property_def["properties"]["blue"]["$ref"].split("/")[-1]
            # typing = "Alliances<{kk}>".format(kk=convert_to_kotlin_case(referenced_definition))

            kotlin_param_data += alliance_template.format(
                name=name, i8=" " * indent8, i12=" " * (indent8 + 4),
                ldef=function_code_for_definition(referenced_definition, "alliance", indent8 + 4))
        else:
            data_type = property_def["type"]

            if data_type == "object":
                # typing = "Map<String, Any?>"
                kotlin_param_data += data_get_call_template.format(name=name, typ="obj", p=property_name)

            elif data_type == "number":
                # typing = "Double"
                kotlin_param_data += data_get_call_template.format(name=name, typ="double", p=property_name)

            elif data_type == "string":
                # typing = "String"
                kotlin_param_data += data_get_call_template.format(name=name, typ="string", p=property_name)

            elif data_type == "integer":
                # typing = "Int"
                kotlin_param_data += data_get_call_template.format(name=name, typ="int", p=property_name)

            elif data_type == "boolean":
                # typing = "Boolean"
                kotlin_param_data += data_get_call_template.format(name=name, typ="boolean", p=property_name)

            elif data_type == "array":
                array_items = property_def["items"]

                if "$ref" in array_items:
                    referenced_definition = array_items["$ref"].split("/")[-1]
                    # typing = convert_to_kotlin_case(referenced_definition)
                    kotlin_param_data += data_get_call_template.format(name=name, typ="genericArray", p=property_name)

                    function_code = function_code_for_definition(
                        referenced_definition, property_name + "Item", indent8)

                    kotlin_param_data += ("?.mapToList { " + property_name + "Item -> \n" +
                                          " " * indent8 + function_code + "}")
                else:
                    array_type = array_items["type"]
                    if array_type == "object":
                        # typing = "List<Map<String, Any?>>"
                        kotlin_param_data += data_get_call_template.format(name=name, typ="objList", p=property_name)

                    elif array_type == "number":
                        # typing = "List<Double>"
                        kotlin_param_data += data_get_call_template.format(name=name, typ="doubleList", p=property_name)

                    elif array_type == "string":
                        # typing = "List<String>"
                        kotlin_param_data += data_get_call_template.format(name=name, typ="stringList", p=property_name)

                    elif array_type == "integer":
                        # typing = "List<Int>"
                        kotlin_param_data += data_get_call_template.format(name=name, typ="intList", p=property_name)

                    elif array_type == "boolean":
                        # typing = "List<Boolean>"
                        kotlin_param_data += data_get_call_template.format(name=name, typ="booleanList",
                                                                           p=property_name)
                    else:
                        print(array_items)
                        raise TypeError()
            else:
                raise TypeError()

        parameter_list.append(kotlin_param_data)

    return_string += ",\n".join(" " * indent4 + x for x in parameter_list)

    return_string += "\n" + " " * indent + ")"

    return return_string


def kotlin_function_for_api_path(path_name, path_def):
    gt = path_def["get"]
    op_id = gt["operationId"]
    des = gt["description"]
    params = gt["parameters"]
    actual_params = []

    for i in range(len(params)):
        param = params[i]
        if "$ref" in param:
            param_name = params[i]["$ref"].split("/")[-1]
            if param_name != "If-Modified-Since":
                actual_params.append(param_name)
        else:
            actual_params.append(param["name"]) #FIXME

    res = gt["responses"]["200"]["content"]["application/json"]["schema"]
    k2 = path_name

    if len(actual_params) == 0:
        ps = ""
    else:
        pdef = map(lambda x: x + ": " + request_parameter_types[x], actual_params)
        ps = "\n    " + ",\n    ".join(pdef) + "\n"
        for p in actual_params:
            k2 = k2.replace("{" + p + "}", "$" + p)

    body = "return "
    fname = "get"

    if "$ref" in res:
        ref_k = res["$ref"].split("/")[-1]
        typing = convert_to_kotlin_case(ref_k)
        body += function_code_for_definition(ref_k, "response", 4)

    elif res["type"] == "array":
        it = res["items"]
        fname = "getArray"
        if "$ref" in it:
            ref_k = it["$ref"].split("/")[-1]
            typing = "List<" + convert_to_kotlin_case(ref_k) + ">"
            body += "response.map { it as JsonObject }.map {\n" + " " * 8 + \
                    function_code_for_definition(ref_k, "it", 8) + "}"
        elif it["type"] == "string":
            typing = "List<String>"
            body += "response.map { it as String }"
        elif it["type"] == "integer":
            typing = "List<Int>"
            body += "response.map { it as Int }"
        elif it["type"] == "object":
            typing = "List<Map<String, Any?>>"
            body += "response.map { it as JsonObject }"
        else:
            raise TypeError()

    elif res["type"] == "object":
        ref_k = res["additionalProperties"]["$ref"].split("/")[-1]
        typing = "Map<String, " + convert_to_kotlin_case(ref_k) + "?>"
        body += "response.mapValues { (it as JsonObject?)!! }.mapValues {\n"
        body += " " * 8 + function_code_for_definition(ref_k, "it.value", 8) + "}"

    else:
        raise TypeError()

    s = function_template.format(des=des, op_id=op_id, params=ps, typing=typing, k=k2, body=body, fname=fname)
    return s


with open("Paths.kt", mode="w") as f:
    print("// API Version", api_version, "\n", file=f)
    print(header, file=f)
    for k, v in paths.items():
        print(kotlin_function_for_api_path(k, v), file=f)
