import json
import pprint
import io

swagger_file = open("api_v3.json")
json_data = swagger_file.read()
swagger_file.close()

data = json.loads(json_data)

api_version = data["info"]["version"]

defs = data["definitions"]

header = """@file:Suppress("unused", "SpellCheckingInspection", "KDocUnresolvedReference")

package ca.warp7.rt.router.tba

import com.beust.klaxon.JsonObject

/**
 * Represents Alliance Data
 */
data class Alliances<T>(

    /**
     * The Blue Alliance
     */
    val blue: T,

    /**
     * The Red Alliance
     */
    val red: T
)"""

template = """

/**
 * {clz}
 * ------------------------------
 * {des}
 */

data class {clz}(
    /**
     * Raw Data Map
     */
    val raw: JsonObject{dat}
){{
    override fun toString(): String {{
        return raw.toJsonString(true)
    }}
}}"""

t2 = """,

    /**
     * {des}
     */
    val {name}: {typing}?"""


def def_2_k(k, v):
    if "properties" in v:
        props = v["properties"]
    else:
        props = {}
    if "description" in v:
        des = v["description"]
    else:
        des = "No description available"
    dat = ""
    for p, q in props.items():
        if "description" in q:
            sdes = q["description"]
        else:
            sdes = "No description available"
        if "$ref" in q:
            ref_k = q["$ref"].split("/")[-1]
            typing = get_kk(ref_k)
        elif p == "alliances":
            ref_k = q["properties"]["blue"]["$ref"].split("/")[-1]
            typing = "Alliances<{kk}?>".format(kk=get_kk(ref_k))
        else:
            dtype = q["type"]
            if dtype == "object":
                typing = "Map<String, Any?>"
            elif dtype == "number":
                typing = "Double"
            elif dtype == "string":
                typing = "String"
            elif dtype == "integer":
                typing = "Int"
            elif dtype == "boolean":
                typing = "Boolean"
            elif dtype == "array":
                it = q["items"]
                if "$ref" in it:
                    ref_k = it["$ref"].split("/")[-1]
                    typing = "List<" + get_kk(ref_k) + ">"
                else:
                    atype = it["type"]
                    if atype == "object":
                        typing = "List<Map<String, Any?>>"
                    elif atype == "number":
                        typing = "List<Double>"
                    elif atype == "string":
                        typing = "List<String>"
                    elif atype == "integer":
                        typing = "List<Int>"
                    elif atype == "boolean":
                        typing = "List<Boolean>"
                    else:
                        print(it)
                        raise TypeError()
            else:
                raise TypeError()

        # reserved words
        if p == "in":
            p = "_in"
        dat += t2.format(des=sdes, name=p, typing=typing)
    s = template.format(des=des, clz=k, dat=dat)
    return s

def get_kk(k):
    sp = k.split("_")
    sl = list(map(lambda x: x[0].capitalize() + x[1:], sp))
    kk = "".join(sl)
    return kk

##with io.StringIO() as io:
##    for k, v in defs.items():
##        kk = get_kk(k)
##        print(def_2_k(kk, v), file=io)
##    print(io.getvalue())

with open("Models.kt", mode="w") as io:
    print(header, file=io)
    for k, v in defs.items():
        kk = get_kk(k)
        print(def_2_k(kk, v), file=io)
    
        

    
