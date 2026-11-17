"""mutations.py DIR: writes fuzzed serialized documents as DIR/N.json, emptying DIR first: three well-formed
documents, every prefix of two of them, and 1,500 seeded mutations."""
import os, random, sys
D = sys.argv[1]
os.makedirs(D, exist_ok=True)
for f in os.listdir(D):
    os.remove(os.path.join(D, f))
bases = [
    '{"quest":1,"types":[{"tuple":[["d","Dynamic"],["u",1],["us",4],["o",5],["v",7],["w",8],["r",9]]},{"auto":{"bound":null,"components":[["fst",2],["snd",2]]}},{"param":0},'
    '{"record":{"a":"String","b":"Int","var c":"Real"}},{"array":1},{"option":{"none":null,"some":6}},{"tuple":[["v","Int"],["var s","String"]]},'
    '{"variant":{"a":"Int","b":"Ok","c":6}},{"external":"uint64_t"},{"array":"Real"}],"type":0,'
    '"value":[{"@type":"Int","@value":42},{"@type":3,"@value":[{"@id":1,"a":"p\\u0041\\n","b":-1,"c":0.5},{"@ref":1}]},[{"@type":"Bool","@value":[true,false]},{"@type":"Ok","@value":[null,null]}],'
    '{"some":[7,"s"]},{"c":{"@id":2,"@items":[1,"t"]}},18446744073709551615,[1.5e-7,"Infinity",-0.0,3]]}',
    '{"quest":1,"types":[{"record":{"id":"Int","var next":1,"var t":2}},{"array":0},{"tuple":[["var n","Int"]]}],"type":0,'
    '"value":{"@id":1,"id":1,"next":{"@id":5,"@items":[{"@id":2,"id":2,"next":[{"@ref":1},{"@ref":2}],"t":{"@id":3,"@items":[4]}}]},"t":{"@ref":3}}}',
    '{"quest":1,"types":[{"tuple":[["t",1],["bx",3],["o",5],["p",8]]},{"abstract":"u/ab.T","rep":2},{"tuple":[["x","Int"],["y","Int"]]},'
    '{"abstract":"u/ab.Box","args":["Real"],"rep":4},{"tuple":[["v","Real"]]},{"abstract":"u/ab.O","rep":6},{"option":{"none":null,"some":7}},{"tuple":[["v","Int"]]},'
    '{"abstract":"u/ab.Pair","args":["Int","String"],"rep":9},{"tuple":[["a","Int"],["b",10]]},{"array":"String"}],"type":0,'
    '"value":[[3,4],[2.5],{"some":[7]},[11,["x","y"]]]}',
]
docs = []
for b in bases:
    docs.append(b)
# every prefix of the first base, every 1 char
for k in range(len(bases[0])):
    docs.append(bases[0][:k])
for k in range(0, len(bases[1]), 2):
    docs.append(bases[1][:k])
rng = random.Random(20261115)
alphabet = '{}[]",:0123456789-+.eE@ntfa\\u xrl'
def mutate(s):
    s = list(s)
    for _ in range(rng.choice([1, 1, 1, 2, 3])):
        op = rng.randrange(4)
        i = rng.randrange(len(s))
        if op == 0:
            s[i] = rng.choice(alphabet)
        elif op == 1:
            del s[i]
        elif op == 2:
            s.insert(i, rng.choice(alphabet))
        else:
            # swap two type refs or digits: replace a digit by another digit
            ds = [j for j, c in enumerate(s) if c.isdigit()]
            if ds:
                s[rng.choice(ds)] = rng.choice("0123456789")
    return "".join(s)
for n in range(1500):
    docs.append(mutate(bases[n % 3]))
for i, d in enumerate(docs):
    with open(os.path.join(D, "%d.json" % i), "wb") as f:
        f.write(d.encode("latin-1"))
print(len(docs))
