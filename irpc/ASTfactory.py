from pycparser.c_ast import FuncCall, For, While, FuncDef, Return, FuncDecl, ExprList, ID, Decl, TypeDecl, IdentifierType, If, BinaryOp, UnaryOp, Compound, Assignment, Constant, Switch, Case

class ASTfactory:

    def __init__(self, entity):
        self.entity = entity

    @property
    def memo_flag_name(self):
        return f'{self.entity}_provided'

    @property
    def c_touch_name(self):
        return f'touch_{self.entity}'

    @property
    def provider(self):
        return f'provide_{self.entity}'

    def gen_memo_flag_node(self,self_touch):
        val = 'true' if self_touch else 'false'
        type_ = TypeDecl(declname = self.memo_flag_name,
                         quals=[], type=IdentifierType(names=['bool']))
        return Decl(name=self.entity, quals=[],
                    storage=[], funcspec=[],
                    type= type_, init=ID(name=val),
                    bitsize=None)

    @property
    def memo_flag_node_self(self):
        return self.gen_memo_flag_node(True)

    @property
    def memo_flag_node(self):
        return self.gen_memo_flag_node(False)

    @property
    def touch_definition_node(self):
        type_ = FuncDecl(args=None,
                         type=TypeDecl(declname=self.c_touch_name,
                                       quals=[], type=IdentifierType(names=['void'])))
        return FuncDef(decl=Decl(name=self.c_touch_name,
                                 quals=[], storage=[],
                                 funcspec=[], type=type_,
                                 init=None, bitsize=None),
                       param_decls=None, body=Compound(block_items=[]))

    @property
    def touch_declaration_node(self):
        return FuncDecl(args=None,
                        type=TypeDecl(declname=self.c_touch_name,
                                      quals=[], type=IdentifierType(names=['void'])))
    @property
    def cached_provider_call(self):
        provider = self.provider
        entity_flag = self.memo_flag_name
        return If(cond=UnaryOp(op='!', expr=ID(name=entity_flag)),
                  iftrue=Compound(block_items=[ FuncCall(name=ID(name=provider), args=None),
                                                Assignment(op='=',
                                                           lvalue=ID(name=entity_flag),
                                                           rvalue=Constant(type='bool', value='true'))]),
                  iffalse=None)


