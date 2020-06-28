import json

swagger_file = open("api_v3.json")
json_data = swagger_file.read()
swagger_file.close()

data = json.loads(json_data)

api_version = data["info"]["version"]

model_schemas = data["components"]["schemas"]

header = """@file:Suppress("unused", "SpellCheckingInspection", "KDocUnresolvedReference")

package kb.plugin.thebluealliance.api

import org.json.JSONObject

/**
 * Alliance Data
 */
class Alliances<T>(val blue: T, val red: T)"""

template = """
{class_description}class {clz}(
    val data: JSONObject{fields}
)"""

class_field_template = """,

    {field_description}val {property_name}: {kotlin_type}?"""


def schema_to_class(key, definition):
    if "properties" in definition:
        properties = definition["properties"]
    else:
        properties = {}

    if "description" in definition:
        description = "/** " + definition["description"] + " */\n"
    else:
        description = ""

    class_fields = ""

    for propperty_name, property_def in properties.items():

        if "description" in property_def:
            field_description = "/** " + property_def["description"] + " */\n    "
        else:
            field_description = ""

        if "$ref" in property_def:
            reference_class = property_def["$ref"].split("/")[-1]
            kotlin_type = convert_to_kotlin_case(reference_class)

        elif propperty_name == "alliances":
            reference_class = property_def["properties"]["blue"]["$ref"].split("/")[-1]
            kotlin_type = "Alliances<{kk}?>".format(kk=convert_to_kotlin_case(reference_class))

        else:
            data_type = property_def["type"]
            if data_type == "object":
                kotlin_type = "JSONObject"
            elif data_type == "number":
                kotlin_type = "Double"
            elif data_type == "string":
                kotlin_type = "String"
            elif data_type == "integer":
                kotlin_type = "Int"
            elif data_type == "boolean":
                kotlin_type = "Boolean"
            elif data_type == "array":
                array_items = property_def["items"]

                if "$ref" in array_items:
                    reference_class = array_items["$ref"].split("/")[-1]
                    kotlin_type = "List<" + convert_to_kotlin_case(reference_class) + ">"
                else:
                    array_type = array_items["type"]
                    if array_type == "object":
                        kotlin_type = "List<JSONObject>"
                    elif array_type == "number":
                        kotlin_type = "List<Double>"
                    elif array_type == "string":
                        kotlin_type = "List<String>"
                    elif array_type == "integer":
                        kotlin_type = "List<Int>"
                    elif array_type == "boolean":
                        kotlin_type = "List<Boolean>"
                    else:
                        print(array_items)
                        raise TypeError()
            else:
                raise TypeError()

        # "in" is reserved in Kotlin
        if propperty_name == "in":
            propperty_name = "_in"

        class_fields += class_field_template.format(
            field_description=field_description, property_name=propperty_name, kotlin_type=kotlin_type)
    return template.format(class_description=description, clz=key, fields=class_fields)


def convert_to_kotlin_case(underscore_case):
    split = underscore_case.split("_")
    return "".join(word[0].capitalize() + word[1:] for word in split)


with open("Models.kt", mode="w") as f:
    print("// The Blue Alliance API Version", api_version, "\n", file=f)
    print(header, file=f)
    for schema_key, schema_definition in model_schemas.items():
        kotlin_name = convert_to_kotlin_case(schema_key)
        print(schema_to_class(kotlin_name, schema_definition), file=f)
