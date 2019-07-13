from irpc.utils import cached_property
from irpc.bindingEntity import entity2Compound, entity2CompoundSimple, touch2entity
from pycparser.c_ast import *
from collections import defaultdict
from irpc.ASTfactory import ASTfactory
import operator

def provider_name(provdef):
    return provdef.decl.name.split('provide_').pop()

class Function():
   def __init__(self, funcdef):
        self.def_ = funcdef

   @cached_property
   def s_entity_name(self):
        return set()

class Provider(Function):

    @cached_property
    def l_entity(self):
        pass
        #return self.def_.decl.type.args.params

    @cached_property
    def s_entity_name(self):
        return set(i for i in self.def_.decl.name.split('provide_') if i)

    @cached_property
    def l_entity_name(self):
        return sorted(self.s_entity_name)

    @cached_property
    def uiid(self):
        return  '__'.join(self.l_entity_name)

    @cached_property
    def provider_name(self):
        return f'provide_{self.uiid}'


class CommWorld():

    def __init__(self, l_func):
        self.l_func = l_func

    @cached_property
    def s_provider_ast(self):
        def is_provider(funcdef):
            return funcdef.decl.name.startswith('provide')

        return { f for f in self.l_func if is_provider(f) }

    @cached_property
    def s_provider(self):
        return {Provider(p) for p in self.s_provider_ast}

    @cached_property
    def l_provider(self):
        return sorted(self.s_provider, key=operator.attrgetter("uiid"), reverse=True)

    @cached_property
    def main(self):
        return next(Function(f) for f in self.l_func if f.decl.name == 'main')

    @cached_property
    def s_provider_and_main(self):
        return self.s_provider | set([self.main])

    @cached_property
    def s_provider_and_main_ast(self):
        return {f.def_ for f in self.s_provider_and_main}

    @cached_property
    def s_entity(self):
        s = set()
        for p in self.s_provider:
            s |= set(p.l_entity_name)
        return s

    @cached_property
    def d_entity2provider(self):
        d = {}
        for p in self.s_provider:
            for entity in p.s_entity_name:
                d[entity] = p.uiid
        return d

    @cached_property
    def child_adjacency_graph(self):
        d = defaultdict(set)
        for p in self.s_provider:
            entity_provided = p.s_entity_name
            for parent_entity, _ in entity2Compound(p.def_.body, self.s_entity - entity_provided).items():
                d[parent_entity] |= entity_provided
        return d

    def entity2provider(self, entity):
        return self.d_entity2provider[entity]

    def insert_provider_calls(self):
        for f in self.s_provider_and_main:
            l_ent_adjusted = self.s_entity - f.s_entity_name
            instance_dict = entity2CompoundSimple(f.def_, l_ent_adjusted, ID)

            d = defaultdict(lambda: defaultdict(set))
            for entity, instances in instance_dict.items():
                for compound, index in instances:
                    d[compound][index].add(entity)

            for compound in d:
                d_idx_entity = d[compound]
                for index in sorted(d_idx_entity, reverse=True):
                    for entity in sorted(d_idx_entity[index]):
                        provider_call = ASTfactory(self.entity2provider(entity)).cached_provider_call
                        compound.block_items.insert(index, provider_call)

    def hoist_declarations(self,
                          context):
    
        for p in self.l_provider:
            l_node = p.def_ .body.block_items
            # Move the declaration of the entity and the top of the file
            # All add the declaration of the flag variable for the memoization
            for i, node in enumerate(l_node):
                if isinstance(node,Decl) and node.type.declname in p.s_entity_name:
                    node = l_node.pop(i)  
                    # Entity Declaration
                    context.insert(0, node)
                    # is_provided Boolean
                    for entname in p.s_entity_name:
                        context.insert(1, ASTfactory(entname).memo_flag_node)
                    break

    def insert_touches_stuff(self,context):

        # When touching inside a while / for statement should ensure that the entity in statement are reprovided
        l_touch = set()
        for p in self.s_provider_and_main_ast:
            for (entity_touched, compound), l_e in touch2entity(p,self.s_entity).items():
                for e in sorted(l_e):
                    provider_call = ASTfactory(e).cached_provider_call
                    compound.block_items.insert(len(compound.block_items), provider_call)
                l_touch.add(entity_touched)

        for entity in sorted(l_touch):
            astfact =  ASTfactory(entity)
            touch_def = astfact.touch_definition_node
            touch_decl = astfact.touch_declaration_node
            
            for ent_touched in sorted(self.child_adjacency_graph[entity]):
                touch_def.body.block_items.insert(1,ASTfactory(ent_touched).memo_flag_node)
            
            context.insert(len(context)-1, touch_def)
            context.insert(0, touch_decl)

