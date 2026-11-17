"""handwritten.py DIR: writes the hand-written serialized documents as DIR/N.json, emptying DIR first: numbers and
scalars at each type, malformed and cyclic type tables, abstract types against u/ab's registry, and sharing."""
import os, sys
D = sys.argv[1]
os.makedirs(D, exist_ok=True)
for f in os.listdir(D):
    os.remove(os.path.join(D, f))
docs = []
def doc(types, typ, value):
    docs.append('{"quest":1,"types":%s,"type":%s,"value":%s}' % (types, typ, value))
def raw(s):
    docs.append(s)

# --- numbers at Int
for v in ["0", "-0", "7", "-7", "1073741823", "1073741824", "-1073741825", "999999999999999999", "1000000000000000000",
          "9223372036854775807", "-9223372036854775808", "9223372036854775808", "-9223372036854775809",
          "99999999999999999999", "123456789012345678901234567890", "-", "+5", "01", "007", "1-2", "1+2", "--1", "1.0", "1e2", "1E2",
          ".5", "e5", "E", "1e", "1.", "1.2.3", "1e+", "-e", "5 ", " 5", "0x10", "1_000", "true", "null", "\"5\"", "[5]", "",
          "1234567890123456789-", "12345678901234567+8", "-1234567890123456789012"]:
    doc("[]", '"Int"', v)
# --- numbers at Real
for v in ["0", "-0", "1", "-1", "1.5", "-0.0", "1e2", "1E2", "1e+2", "1e-2", "1e999", "-1e999", "1e-999", "5e-324", "4.9e-324",
          "2.5e-324", "1.7976931348623157e308", "1.7976931348623159e308", "0.1", "0.30000000000000004", "123456789012345678",
          "1234567890123456789", "9223372036854775807", "9223372036854775808", "99999999999999999999", "100000000000000000000",
          "-9223372036854775809", ".5", "5.", "1e", "1e+", "1.2.3", "1e5e5", "e", "-", "-.5", "-e5", "1.e5", "+1.5", "\"Infinity\"",
          "\"-Infinity\"", "\"NaN\"", "\"infinity\"", "\"+Infinity\"", "true", "null",
          "0.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001",
          "1" + "0" * 120 + ".0", "1" + "0" * 400 + ".0", "0." + "0" * 400 + "1", "1.00000000000000011102230246251565404236316680908203125",
          "1.00000000000000011102230246251565404236316680908203124", "1.00000000000000011102230246251565404236316680908203126",
          "9007199254740993.0", "9007199254740993", "1e23", "8.5e-320", "-", "--1.5", "1.5-", "1.5+2", "1e5.5", "1-e5"]:
    doc("[]", '"Real"', v)
# --- words
W = '[{"external":"uint64_t"}]'
for v in ["0", "5", "18446744073709551615", "18446744073709551616", "18446744073709551614", "9223372036854775808", "-1", "-0",
          "00000000000000000000005", "99999999999999999999", "184467440737095516150", "1.0", "\"5\"", "1844674407370955161+",
          "18446744073709551+15", "0018446744073709551615", "19999999999999999999", "20000000000000000000", "1e3"]:
    doc(W, "0", v)
doc('[{"external":"int64_t"}]', "0", "5")
doc('[{"external":5}]', "0", "5")
# --- literals, strings, chars
for t, v in [("Bool", "true"), ("Bool", "false"), ("Bool", "txxx"), ("Bool", "tru"), ("Bool", "fxxxx"), ("Bool", "falsy"), ("Bool", "True"),
             ("Bool", "1"), ("Bool", "\"true\""), ("Ok", "null"), ("Ok", "nxxx"), ("Ok", "nul"), ("Ok", "0"), ("Ok", "[]"),
             ("Bool", "truex"), ("Ok", "nulll"),
             ("Char", "\"a\""), ("Char", "\"\""), ("Char", "\"ab\""), ("Char", "\"\\u0041\""), ("Char", "\"\\u00ff\""), ("Char", "\"\\u0100\""),
             ("Char", "\"\\n\""), ("Char", "\"\\/\""), ("Char", "5"), ("Char", "\"\xc3\xa9\""),
             ("String", "\"\""), ("String", "\"a\\\"b\\\\c\\/d\\be\\ff\\ng\\rh\\ti\""), ("String", "\"\\u0000\\u007f\\u0080\\u00FF\\u00aB\""),
             ("String", "\"\\u00g0\""), ("String", "\"\\u00\""), ("String", "\"\\x41\""), ("String", "\"\\a\""), ("String", "\"abc"),
             ("String", "\"abc\\"), ("String", "\"abc\\u00"), ("String", "\"tab\there\""), ("String", "\"nl\nhere\""), ("String", "'a'"),
             ("String", "\"\\uD83D\\uDE00\""), ("String", "\"\\u0041\\u0042\""), ("String", "5"), ("String", "\"\\U0041\""),
             ("String", "\"" + "x" * 5000 + "\""), ("String", "\"\x01\x02\x7f\""), ("String", "\"\xff\xfe\"")]:
    doc("[]", '"%s"' % t, v)
# --- root shape
raw('')
raw('   ')
raw('{}')
raw('[]')
raw('5')
raw('"x"')
raw('{"quest":1,"types":[],"type":"Int"}')
raw('{"quest":1,"types":[],"type":"Int","value":5,"extra":1}')
raw('{"quest":2,"types":[],"type":"Int","value":5}')
raw('{"quest":1.0,"types":[],"type":"Int","value":5}')
raw('{"quest":"1","types":[],"type":"Int","value":5}')
raw('{"quest":01,"types":[],"type":"Int","value":5}')
raw('{"quest":1,"types":{},"type":"Int","value":5}')
raw('{"quest":1,"types":null,"type":"Int","value":5}')
raw('{"quest":1,"type":"Int","value":5,"value":6}')
raw('{"quest":1,"types":[],"type":"Int","type":"Real","value":5}')
raw('{"quest":1,"quest":2,"types":[],"type":"Int","value":5}')
raw('{"quest":2,"quest":1,"types":[],"type":"Int","value":5}')
raw('{"quest":1,"types":[],"types":[{"array":"Int"}],"type":"Int","value":5}')
raw('["quest",1,"types",[]]')
raw('{"value":5,"type":"Int","types":[],"quest":1}')
raw(' \t\r\n{ "quest" : 1 , "types" : [ ] , "type" : "Int" , "value" : 5 } trailing')
raw('{"quest":1,"types":[],"type":"Int","value":5}{"quest":1,"types":[],"type":"Int","value":6}')
raw('{"quest":1,"types":[],"type":"Int","value":5,}')
raw('{"quest":1,"types":[],"type":"Int","value":5')
raw('{"quest":1,"types":[],"type":"Int","value":')
raw('{"quest":1,"types":[],"type":"Int","value"')
raw('{"quest":1,"types":[],"type":"Int",')
raw('{"quest":1,"types":[')
raw('{"quest"')
raw('{"quest":1 "types":[],"type":"Int","value":5}')
raw('{quest:1,"types":[],"type":"Int","value":5}')
raw('{"quest":1,"types":[],"type":"Nope","value":5}')
raw('{"quest":1,"types":[],"type":0,"value":5}')
raw('{"quest":1,"types":[],"type":-1,"value":5}')
raw('{"quest":1,"types":[],"type":null,"value":5}')
raw('{"quest":1,"types":[],"type":1.0,"value":5}')
raw('{"quest":1,"types":[{"array":"Int"}],"type":1,"value":[]}')
raw('{"quest":1,"types":[{"array":"Int"}],"type":99999999999999999999,"value":[]}')
raw('{"quest":1,"types":[{"array":"Int"}],"type":18446744073709551616,"value":[]}')
# --- arrays and tuples
A = '[{"array":"Int"}]'
for v in ["[]", "[1,2,3]", "[ 1 , 2 ]", "[1,]", "[,1]", "[1 2]", "[1,2", "[", "]", "[[1]]", "[1.5]", "{}", "{\"@items\":[1]}",
          "{\"@id\":1,\"@items\":[1]}", "{\"@id\":1}", "{\"@id\":1,\"@items\":[1],\"x\":1}", "{\"@id\":\"a\",\"@items\":[1]}",
          "{\"@id\":1.5,\"@items\":[1]}", "{\"@ref\":1}", "{\"@ref\":1,\"@id\":2}", "{\"@id\":1,\"@items\":{}}", "null", "5",
          "{\"@id\":-5,\"@items\":[1]}", "{\"@id\":0,\"@items\":[1]}", "{\"@items\":[1],\"@id\":1}", "{\"@id\":1,\"@id\":2}"]:
    doc(A, "0", v)
AA = '[{"array":1},{"array":"Int"}]'
for v in ['[{"@id":1,"@items":[1]},{"@ref":1}]', '[{"@ref":1},{"@id":1,"@items":[1]}]', '[{"@id":1,"@items":[1]},{"@id":1,"@items":[2]}]',
          '[{"@id":1,"@items":[1]},{"@ref":2}]', '[{"@id":1,"@items":[1]},{"@ref":"1"}]', '[{"@id":1,"@items":[1]},{"@ref":1.0}]',
          '[{"@id":7,"@items":[1]},{"@id":3,"@items":[]},{"@ref":3},{"@ref":7}]', '{"@id":1,"@items":[{"@ref":1}]}',
          '[{"@id":99999999999999999999,"@items":[1]},{"@ref":9223372036854775807}]']:
    doc(AA, "0", v)
# recursive array type Array(Array(...)) referencing itself
doc('[{"array":0}]', "0", '{"@id":1,"@items":[{"@ref":1},[],[[]]]}')
T = '[{"tuple":[["a","Int"],["var b","String"],["","Bool"]]}]'
for v in ['[1,"x",true]', '[1,"x"]', '[1,"x",true,4]', '[]', '{"@id":1,"@items":[1,"x",true]}', '["x",1,true]', '{"a":1}', 'null']:
    doc(T, "0", v)
doc('[{"tuple":[]}]', "0", "[]")
doc('[{"tuple":[]}]', "0", "[1]")
doc('[{"tuple":[]}]', "0", '{"@id":1,"@items":[]}')
doc('[{"tuple":{}}]', "0", "[]")
doc('[{"tuple":[["a"]]}]', "0", "[]")
doc('[{"tuple":[["a","Int","x"]]}]', "0", "[1]")
doc('[{"tuple":[[1,"Int"]]}]', "0", "[1]")
doc('[{"tuple":[["var","Int"],["var ","Int"],["var  x","Int"],["variable","Int"]]}]', "0", "[1,2,3,4]")
doc('[{"tuple":[["a",5]]}]', "0", "[1]")
doc('[{"tuple":[["a",0]]}]', "0", '{"@id":1,"@items":[{"@ref":1}]}')
# subtyping at refs: tuple prefix
doc('[{"tuple":[["a",1],["b",2]]},{"tuple":[["x","Int"],["y","Int"]]},{"tuple":[["x","Int"]]}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
doc('[{"tuple":[["a",2],["b",1]]},{"tuple":[["x","Int"],["y","Int"]]},{"tuple":[["x","Int"]]}]', "0", '[{"@id":1,"@items":[1]},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"tuple":[["x","Int"],["y","Int"]]},{"array":"Int"}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"array":"Int"},{"array":"Real"}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
# --- records
R = '[{"record":{"x":"Int","var y":"String"}}]'
for v in ['{"x":1,"y":"s"}', '{"y":"s","x":1}', '{"x":1}', '{"x":1,"y":"s","z":1}', '{"@id":1,"x":1,"y":"s"}', '{"x":1,"y":"s","@id":1}',
          '{"x":1,"x":2}', '{"x":1,"x":2,"y":"s"}', '{"x":1,"var y":"s"}', '[1,"s"]', '{"@ref":1}', '{"@id":1,"@id":2,"x":1,"y":"s"}',
          '{"x":"s","y":1}', 'null', '{"@id":"k","x":1,"y":"s"}']:
    doc(R, "0", v)
doc('[{"record":{}}]', "0", "{}")
doc('[{"record":{}}]', "0", "[]")
doc('[{"record":{}}]', "0", '{"@id":1}')
doc('[{"record":[]}]', "0", "{}")
doc('[{"record":{"b":"Int","a":"Int","var c":"Int","B":"Int","":"Int"}}]', "0", '{"a":1,"b":2,"c":3,"B":4,"":5}')
doc('[{"record":{"x":"Int","x":"String"}}]', "0", '{"x":1}')
doc('[{"record":{"x":"Int","x":"String"}}]', "0", '{"x":1,"x":"s"}')
doc('[{"record":{"x":"Int","var x":"String"}}]', "0", '{"x":1,"x":"s"}')
doc('[{"record":{"@id":"Int"}}]', "0", '{"@id":1}')
doc('[{"record":{"@ref":"Int"}}]', "0", '{"@ref":1}')
doc('[{"record":{"x":0}}]', "0", '{"@id":1,"x":{"@ref":1}}')
doc('[{"record":{"x":0}}]', "0", '{"x":{"@ref":1}}')
# record seen at two types
RR = '[{"tuple":[["a",1],["b",2]]},{"record":{"x":"Int","var y":"String"}},{"record":{"x":"Int"}}]'
doc(RR, "0", '[{"@id":1,"x":1,"y":"s"},{"@ref":1}]')
doc('[{"tuple":[["a",2],["b",1]]},{"record":{"x":"Int","var y":"String"}},{"record":{"x":"Int"}}]', "0", '[{"@id":1,"x":1},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"record":{"x":"Int","var y":"String"}},{"record":{"y":"String"}}]', "0", '[{"@id":1,"x":1,"y":"s"},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"record":{"x":"Int","var y":"String"}},{"record":{"var y":"String"}}]', "0", '[{"@id":1,"x":1,"y":"s"},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"record":{"x":"Int","var y":"String"}},{"record":{"var x":"Int"}}]', "0", '[{"@id":1,"x":1,"y":"s"},{"@ref":1}]')
# record with a record field stored at a wider type, read at narrower through ref
doc('[{"tuple":[["a",1],["b",3]]},{"record":{"f":2}},{"record":{"x":"Int","y":"Int"}},{"record":{"f":4}},{"record":{"x":"Int"}}]', "0",
    '[{"@id":1,"f":{"x":1,"y":2}},{"@ref":1}]')
# --- options and variants
O = '[{"option":{"none":null,"some":1,"two":2,"zed":3}},{"tuple":[["v","Int"]]},{"tuple":[["a","Int"],["var b","String"]]},{"tuple":[]}]'
for v in ['"none"', '{"some":[4]}', '{"two":[1,"s"]}', '{"zed":[]}', '"zed"', '"some"', '{"none":[]}', '{"none":null}', '{"some":4}',
          '{"some":[4,5]}', '{"some":[]}', '"nope"', '{"nope":[1]}', '{"some":[4],"two":[1,"s"]}', '{}', '[4]', 'null', '0',
          '{"some":{"@id":1,"@items":[4]}}', '{"@ref":1}']:
    doc(O, "0", v)
doc('[{"option":{"b":null,"a":null,"c":null}}]', "0", '"c"')
doc('[{"option":{"a":"Int"}}]', "0", '{"a":5}')
doc('[{"option":{"a":1}},{"array":"Int"}]', "0", '{"a":[5]}')
doc('[{"option":{"a":null,"a":null}}]', "0", '"a"')
doc('[{"option":{"a":null,"a":1}},{"tuple":[["v","Int"]]}]', "0", '"a"')
doc('[{"option":{"a":null,"a":1}},{"tuple":[["v","Int"]]}]', "0", '{"a":[1]}')
doc('[{"option":{}}]', "0", '"a"')
doc('[{"option":[]}]', "0", '"a"')
doc('[{"option":{"var a":1}},{"tuple":[["v","Int"]]}]', "0", '{"var a":[1]}')
doc('[{"option":{"var a":1}},{"tuple":[["v","Int"]]}]', "0", '{"a":[1]}')
doc('[{"option":{"cons":1,"nil":null}},{"tuple":[["head","Int"],["tail",0]]}]', "0", '{"cons":[1,{"cons":[2,"nil"]}]}')
V = '[{"variant":{"a":"Int","b":"String","c":"Ok","d":1,"var e":"Int","f":2}},{"tuple":[["x","Int"]]},{"record":{"r":"Real"}}]'
for v in ['{"a":3}', '{"b":"s"}', '"c"', '{"c":null}', '{"d":[1]}', '{"e":9}', '{"var e":9}', '{"f":{"r":1.5}}', '{"f":{"@id":1,"r":2}}',
          '"a"', '{"a":"s"}', '{"z":1}', '"z"', '{}', '{"a":1,"b":"s"}', '3', 'null', '[3]']:
    doc(V, "0", v)
doc('[{"variant":{"b":"Int","a":"Int","var a":"String"}}]', "0", '{"a":1}')
doc('[{"variant":{"a":null}}]', "0", '"a"')
doc('[{"variant":{"a":null}}]', "0", '{"a":null}')
doc('[{"variant":{}}]', "0", '"a"')
# variant in array, shared tuple payload
doc('[{"array":1},{"variant":{"d":2}},{"tuple":[["x","Int"]]}]', "0", '[{"d":{"@id":1,"@items":[5]}},{"d":{"@ref":1}}]')
# --- Dynamic nested
doc("[]", '"Dynamic"', '{"@type":"Int","@value":3}')
doc("[]", '"Dynamic"', '{"@value":3,"@type":"Int"}')
doc("[]", '"Dynamic"', '{"@type":"Int"}')
doc("[]", '"Dynamic"', '{"@type":"Int","@value":3,"x":1}')
doc("[]", '"Dynamic"', '{"@type":"Int","@type":"Real","@value":3}')
doc("[]", '"Dynamic"', '{"@type":"Dynamic","@value":{"@type":"Dynamic","@value":{"@type":"String","@value":"deep"}}}')
doc("[]", '"Dynamic"', '{"@type":0,"@value":3}')
doc("[]", '"Dynamic"', '3')
doc("[]", '"Dynamic"', '[3]')
doc('[{"array":"Dynamic"},{"array":"Int"}]', "0", '[{"@type":1,"@value":{"@id":1,"@items":[1]}},{"@type":1,"@value":{"@ref":1}},{"@type":"Int","@value":1}]')
# --- autos
AU = '[{"auto":{"bound":null,"components":[["fst",1],["snd",1]]}},{"param":0}]'
for v in ['{"@type":"Int","@value":[6,7]}', '{"@type":"Int","@value":[6]}', '{"@type":"Int","@value":[6,"x"]}', '{"@type":"String","@value":["a","b"]}',
          '{"@type":1,"@value":[6,7]}', '{"@type":0,"@value":[{"@type":"Int","@value":[1,2]},{"@type":"Bool","@value":[true,false]}]}',
          '{"@type":"Int","@value":6}', '[6,7]', '{"@type":"Dynamic","@value":[{"@type":"Int","@value":1},{"@type":"Real","@value":1}]}']:
    doc(AU, "0", v)
doc('[{"param":0}]', "0", "5")
doc('[{"param":1}]', "0", "5")
doc('[{"param":-1}]', "0", "5")
doc('[{"param":63}]', "0", "5")
doc('[{"param":64}]', "0", "5")
doc('[{"param":"0"}]', "0", "5")
doc('[{"array":1},{"param":0}]', "0", "[5]")
doc('[{"auto":{"bound":null,"components":[["a",1]]}},{"param":1}]', "0", '{"@type":"Int","@value":[6]}')
doc('[{"auto":{"bound":null,"components":[["a",1],["inner",2]]}},{"param":0},{"auto":{"bound":null,"components":[["b",1],["a2",3]]}},{"param":1}]', "0",
    '{"@type":"Int","@value":[1,{"@type":"String","@value":["s",2]}]}')
doc('[{"auto":{"bound":null,"components":[["a",1],["inner",2]]}},{"param":0},{"auto":{"bound":null,"components":[["b",1],["a2",3]]}},{"param":1}]', "0",
    '{"@type":"Int","@value":[1,{"@type":"String","@value":["s","t"]}]}')
doc('[{"auto":{"bound":2,"components":[["a",1],["var n","Int"]]}},{"param":0},{"record":{"x":"Int"}},{"record":{"x":"Int","y":"Int"}}]', "0",
    '{"@type":3,"@value":[{"x":1,"y":2},5]}')
doc('[{"auto":{"bound":2,"components":[["a",1],["var n","Int"]]}},{"param":0},{"record":{"x":"Int"}},{"record":{"y":"Int"}}]', "0",
    '{"@type":3,"@value":[{"y":2},5]}')
doc('[{"auto":{"bound":2,"components":[["a",1]]}},{"param":0},{"record":{"x":"Int"}}]', "0", '{"@type":"Int","@value":[5]}')
doc('[{"auto":{"components":[["a",1]]}},{"param":0}]', "0", '{"@type":"Int","@value":[5]}')
doc('[{"auto":{"bound":null}},{"param":0}]', "0", '{"@type":"Int","@value":[5]}')
doc('[{"auto":{"bound":null,"components":[["a",1]],"x":1}},{"param":0}]', "0", '{"@type":"Int","@value":[5]}')
doc('[{"auto":{"bound":null,"components":{}}},{"param":0}]', "0", '{"@type":"Int","@value":[]}')
doc('[{"auto":{"bound":null,"components":[]}}]', "0", '{"@type":"Int","@value":[]}')
doc('[{"auto":[]}]', "0", '{"@type":"Int","@value":[]}')
doc('[{"auto":{"bound":null,"components":[["a",0]]}}]', "0", '{"@type":"Int","@value":[{"@type":"Int","@value":[{"@type":"Int","@value":[]}]}]}')
# --- functions, exceptions (types ok, values not)
doc('[{"array":1},{"fun":{"params":[["","Int"],["var","Real"],["out","Bool"]],"result":"Int"}}]', "0", "[]")
doc('[{"array":1},{"fun":{"params":[["x","Int"]],"result":"Int"}}]', "0", "[]")
doc('[{"array":1},{"fun":{"params":[],"result":"Int"}}]', "0", "[]")
doc('[{"array":1},{"fun":{"params":[]}}]', "0", "[]")
doc('[{"array":1},{"fun":{"result":"Int"}}]', "0", "[]")
doc('[{"array":1},{"fun":{"params":{},"result":"Int"}}]', "0", "[]")
doc('[{"array":1},{"fun":[]}]', "0", "[]")
doc('[{"array":1},{"fun":{"params":[],"result":"Int","x":1}}]', "0", "[]")
doc('[{"fun":{"params":[],"result":"Int"}}]', "0", "null")
doc('[{"array":1},{"exception":"Ok"}]', "0", "[]")
doc('[{"array":1},{"exception":"Int"}]', "0", "[]")
doc('[{"exception":"Ok"}]', "0", "null")
# --- type table shape
doc('[5]', "0", "5")
doc('["Int"]', "0", "5")
doc('[{}]', "0", "5")
doc('[{"array":"Int","tuple":[]}]', "0", "[]")
doc('[{"nope":"Int"}]', "0", "5")
doc('[{"array":"Nope"}]', "0", "[]")
doc('[{"array":1}]', "0", "[]")
doc('[{"array":-1}]', "0", "[]")
doc('[{"array":null}]', "0", "[]")
doc('[{"array":"Int"},{"nope":1}]', "0", "[]")
doc('[{"array":"Int"},5]', "0", "[]")
# --- abstract types
AB = "u/ab."
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["x","Int"],["y","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["x","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["p","Int"],["q","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["x","Int"],["var y","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["x","Int"],["y","Real"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":1},{"tuple":[["x","Int"],["y","Int"],["z","Int"]]}]', "0", "[1,2,3]")
doc('[{"abstract":"u/ab.N","rep":"Int"}]', "0", "7")
doc('[{"abstract":"u/ab.N","rep":"Real"}]', "0", "7")
doc('[{"abstract":"u/ab.N","rep":"String"}]', "0", "\"7\"")
doc('[{"abstract":"u/ab.X","rep":"Real"}]', "0", "7.5")
doc('[{"abstract":"u/ab.X","rep":"Int"}]', "0", "7")
doc('[{"abstract":"u/ab.O","rep":1},{"option":{"none":null,"some":2}},{"tuple":[["v","Int"]]}]', "0", '{"some":[7]}')
doc('[{"abstract":"u/ab.O","rep":1},{"option":{"none":null,"some":2,"more":null}},{"tuple":[["v","Int"]]}]', "0", '{"some":[7]}')
doc('[{"abstract":"u/ab.Box","args":["Int"],"rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","args":["Int"],"rep":1},{"tuple":[["v","Real"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","args":["Real"],"rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","args":[],"rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","args":["Int","Int"],"rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.Box","args":"Int","rep":1},{"tuple":[["v","Int"]]}]', "0", "[1]")
doc('[{"abstract":"u/ab.T","args":["Int"],"rep":1},{"tuple":[["x","Int"],["y","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":1,"extra":1},{"tuple":[["x","Int"],["y","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T"},{"tuple":[["x","Int"],["y","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":5,"rep":"Int"}]', "0", "5")
doc('[{"abstract":"u/ab.T","rep":1,"rep":2},{"tuple":[["x","Int"],["y","Int"]]},{"tuple":[["x","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.T","rep":2,"rep":1},{"tuple":[["x","Int"],["y","Int"]]},{"tuple":[["x","Int"]]}]', "0", "[1,2]")
doc('[{"abstract":"u/ab.Box","args":[1],"rep":3},{"abstract":"u/ab.T","rep":2},{"tuple":[["x","Int"],["y","Int"]]},{"tuple":[["v",1]]}]', "0", "[[1,2]]")
doc('[{"abstract":"u/ab.Box","args":[1],"rep":3},{"abstract":"u/ab.Box","args":["Real"],"rep":2},{"tuple":[["v","Real"]]},{"tuple":[["v",1]]}]', "0", "[[1.5]]")
doc('[{"abstract":"u/ab.Pair","args":["Int","String"],"rep":1},{"tuple":[["a","Int"],["b",2]]},{"array":"String"}]', "0", '[1,["s","s"]]')
doc('[{"abstract":"u/ab.Pair","args":["String","Int"],"rep":1},{"tuple":[["a","Int"],["b",2]]},{"array":"String"}]', "0", '[1,["s","s"]]')
doc('[{"abstract":"elsewhere.T","rep":"Int"}]', "0", "42")
doc('[{"abstract":"elsewhere.T","args":["Int"],"rep":1},{"array":"Int"}]', "0", "[42]")
doc('[{"abstract":"elsewhere.T","rep":0}]', "0", "42")
doc('[{"abstract":"elsewhere.T","rep":1},{"abstract":"elsewhere.U","rep":0}]', "0", "42")
doc('[{"abstract":"word.T","rep":"Int"}]', "0", "42")
doc('[{"abstract":"word.T","rep":"Int"}]', "0", "18446744073709551615")
doc('[{"tuple":[["a",1],["b",1]]},{"abstract":"u/ab.T","rep":2},{"tuple":[["x","Int"],["y","Int"]]}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
doc('[{"tuple":[["a",1],["b",2]]},{"abstract":"u/ab.T","rep":2},{"tuple":[["x","Int"],["y","Int"]]}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
doc('[{"tuple":[["a",2],["b",1]]},{"abstract":"u/ab.T","rep":2},{"tuple":[["x","Int"],["y","Int"]]}]', "0", '[{"@id":1,"@items":[1,2]},{"@ref":1}]')
# --- nesting depth (moderate)
doc('[{"array":0}]', "0", "[" * 200 + "]" * 200)
for i, d in enumerate(docs):
    with open(os.path.join(D, "%d.json" % i), "wb") as f:
        f.write(d.encode("latin-1"))
print(len(docs))
