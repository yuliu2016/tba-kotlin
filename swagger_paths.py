import json
import pprint
import io

swagger_file = open("api_v3.json")
json_data = swagger_file.read()
swagger_file.close()

data = json.loads(json_data)

api_version = data["info"]["version"]
paths = data["paths"]
defs = data["definitions"]

header = """@file:Suppress("unused", "SpellCheckingInspection", "KDocUnresolvedReference", "UNUSED_VARIABLE")

package ca.warp7.rt.router.tba

import com.beust.klaxon.JsonObject"""

ft = """

/**
 * {des}
 */
suspend fun TBA.{op_id}({params}): {typing} {{
    val response = {fname}("{k}")
    {body}
}}"""

params_dict = {
    "page_num": "Int",
    "year": "Int",
    "media_tag": "String",
    "team_key": "String",
    "event_key": "String",
    "match_key": "String",
    "district_key": "String"
}

letfmt = """{name}.obj("{p}")?.let {{ {p} ->
{i8}{ldef}
{i4}}}"""

prim = """{name}.{typ}("{p}")"""

alliance = """Alliances(
{i8}blue = {name}.obj("blue")?.let {{ alliance ->
{i12}{ldef}
{i8}}},
{i8}red = {name}.obj("blue")?.let {{ alliance ->
{i12}{ldef}
{i8}}}
)"""

def get_kk(k):
    sp = k.split("_")
    sl = list(map(lambda x: x[0].capitalize() + x[1:], sp))
    kk = "".join(sl)
    return kk

def obj_for_def(ref_k, name, indent):
    p4 = indent + 4
    p8 = indent + 8
    v = defs[ref_k]
    if "properties" in v:
        props = v["properties"]
    else:
        props = {}
    kk = get_kk(ref_k)
    dat = kk + "(\n"
    pz = ["raw = " + name]
    for p, q in props.items():
        # reserved words
        if p == "in":
            dcp = "_in"
        else:
            dcp = p
        argdat = dcp + " = "
        if "$ref" in q:
            ref_k = q["$ref"].split("/")[-1]
            argdat += letfmt.format(name=name, p=p, i8=" "*p8, i4 = " "*p4, ldef= obj_for_def(ref_k, p, p8))
        elif p == "alliances":
            ref_k = q["properties"]["blue"]["$ref"].split("/")[-1]
            typing = "Alliances<{kk}>".format(kk=get_kk(ref_k))
            argdat += alliance.format(name=name, i8=" "*p8, i12=" "*(p8 + 4), ldef = obj_for_def(ref_k, "alliance", p8 + 4))
        else:
            dtype = q["type"]
            if dtype == "object":
                typing = "Map<String, Any?>"
                argdat += prim.format(name=name, typ="obj", p=p)
            elif dtype == "number":
                typing = "Double"
                argdat += prim.format(name=name, typ="double", p=p)
            elif dtype == "string":
                typing = "String"
                argdat += prim.format(name=name, typ="string", p=p)
            elif dtype == "integer":
                typing = "Int"
                argdat += prim.format(name=name, typ="int", p=p)
            elif dtype == "boolean":
                typing = "Boolean"
                argdat += prim.format(name=name, typ="boolean", p=p)
            elif dtype == "array":
                it = q["items"]
                if "$ref" in it:
                    ref_k = it["$ref"].split("/")[-1]
                    typing = get_kk(ref_k)
                    argdat += prim.format(name=name, typ="genericArray", p=p)
                    argdat += "?.mapToList { " + p + "Item -> \n" + " "*p8 + obj_for_def(ref_k, p + "Item", p8) + "}"
                else:
                    atype = it["type"]
                    if atype == "object":
                        typing = "List<Map<String, Any?>>"
                        argdat += prim.format(name=name, typ="objList", p=p)
                    elif atype == "number":
                        typing = "List<Double>"
                        argdat += prim.format(name=name, typ="doubleList", p=p)
                    elif atype == "string":
                        typing = "List<String>"
                        argdat += prim.format(name=name, typ="stringList", p=p)
                    elif atype == "integer":
                        typing = "List<Int>"
                        argdat += prim.format(name=name, typ="intList", p=p)
                    elif atype == "boolean":
                        typing = "List<Boolean>"
                        argdat += prim.format(name=name, typ="booleanList", p=p)
                    else:
                        print(it)
                        raise TypeError()
            else:
                raise TypeError()
        pz.append(argdat)
    dat += ",\n".join(map(lambda x: " " * p4 + x, pz))
    dat += "\n" + " " * indent + ")"
    return dat

def func_for_kk(k, v):
    gt = v["get"]
    op_id = gt["operationId"]
    des = gt["description"]
    params = gt["parameters"]
    actual_params = []
    for i in range(len(params)):
        param_name = params[i]["$ref"].split("/")[-1]
        if param_name != "If-Modified-Since":
            actual_params.append(param_name)
    res = gt["responses"]["200"]["schema"]
    k2 = k
    if (len(actual_params)==0):
        ps = ""
    else:
        pdef = map(lambda x: x + ": " + params_dict[x], actual_params)
        ps = "\n    " + ",\n    ".join(pdef) + "\n"
        for p in actual_params:
            k2 = k2.replace("{" + p + "}", "$" + p)
    body = "return "
    fname = "get"
    if "$ref" in res:
        ref_k = res["$ref"].split("/")[-1]
        typing = get_kk(ref_k)
        body += obj_for_def(ref_k, "response", 4)
    elif res["type"] == "array":
        it = res["items"]
        fname= "getArray"
        if "$ref" in it:
            ref_k = it["$ref"].split("/")[-1]
            typing = "List<" + get_kk(ref_k) + ">"
            body += "response.map { it as JsonObject }.map {\n" + " " * 8 + obj_for_def(ref_k, "it", 8) + "}"
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
        typing = "Map<String, " + get_kk(ref_k) + "?>"
        body += "response.mapValues { (it as JsonObject?)!! }.mapValues {\n"
        body += " " * 8 + obj_for_def(ref_k, "it.value", 8) + "}"
    else:
        raise TypeError()
        
    s = ft.format(des=des, op_id=op_id, params=ps, typing=typing, k=k2, body=body, fname=fname)
    return s

with open("Paths.kt", mode="w") as io:
    print(header, file=io)
    for k, v in paths.items():
        print(func_for_kk(k, v), file=io)
        
