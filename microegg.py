# Based on https://github.com/mwillsey/microegg
from dataclasses import dataclass, field

type Id = int


class Pattern:
    pass


@dataclass(frozen=True)
class Var(Pattern):
    name: str


@dataclass(frozen=True)
class PApp(Pattern):
    f: str
    args: tuple[Pattern, ...]


type Node = tuple[str, tuple[Id, ...]]
type Subst = dict[str, Id]


@dataclass
class EGraph:
    memo: dict[object, Id] = field(default_factory=dict)
    uf: list[Id] = field(default_factory=list)

    def _add(self, obj: object) -> Id:
        id = self.memo.get(obj)
        if id is not None:
            return self.find(id)
        else:
            id = len(self.uf)
            self.uf.append(id)
            self.memo[obj] = id
            return id

    def add_app(self, f: str, *args: Id) -> Id:
        assert all(isinstance(arg, int) for arg in args)
        return self._add((f, args))

    def find(self, id: Id) -> Id:
        while self.uf[id] != id:
            id = self.uf[id]
        return id

    def union(self, id1: Id, id2: Id):
        a, b = self.find(id1), self.find(id2)
        if a != b:
            self.uf[a] = b

    def nodes_in_class(self, id: Id) -> list[object]:
        id = self.find(id)
        return [obj for obj, obj_id in self.memo.items() if self.find(obj_id) == id]

    def is_eq(self, a: Id, b: Id) -> bool:
        return self.find(a) == self.find(b)

    def canonize_node(self, node: Node) -> Node:
        f, args = node
        canon_args = tuple(self.find(arg) for arg in args)
        return (f, canon_args)

    def rebuild(self):
        copy_memo = self.memo.copy()
        while True:
            done = True
            for obj, id in copy_memo.items():
                id = self.find(id)
                new_node = self.canonize_node(obj)
                new_id = self._add(new_node)
                if new_id != id:
                    self.union(id, new_id)
                    done = False
            if done:
                return

    def ematch(self, pattern: Pattern, id: Id) -> list[Subst]:
        return self.ematch_rec(pattern, id, {})

    def ematch_rec(self, pattern: Pattern, id: Id, subst: Subst) -> list[Subst]:
        id = self.find(id)
        match pattern:
            case Var(name):
                if name in subst:
                    if self.is_eq(subst[name], id):
                        return [subst]
                    else:
                        return []
                else:
                    return [{**subst, name: id}]
            case PApp(f, args):
                results = []
                for obj in self.nodes_in_class(id):
                    match obj:
                        case (f0, arg_ids) if f0 == f and len(arg_ids) == len(args):
                            todo = [subst]
                            for arg_pattern, arg_id in zip(args, arg_ids):
                                todo = [
                                    subst1
                                    for subst0 in todo
                                    for subst1 in self.ematch_rec(
                                        arg_pattern, arg_id, subst0
                                    )
                                ]
                            results.extend(todo)
                        case _:
                            raise ValueError(f"Unexpected object in e-graph: {obj}")
                return results


def test_egraph():
    E = EGraph()
    a = E.add_app("a")
    b = E.add_app("b")
    fa = E.add_app("f", a)
    fb = E.add_app("f", b)
    E.union(a, b)
    assert E.is_eq(a, b)
    assert not E.is_eq(fa, fb)
    E.rebuild()
    assert E.is_eq(a, b)
    assert E.is_eq(fa, fb)

    assert len(E.ematch(PApp("f", (Var("x"),)), E.find(fa))) == 2


if __name__ == "__main__":
    test_egraph()
