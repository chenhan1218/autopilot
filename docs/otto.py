from sphinx.util.compat import Directive
from sphinx.util.compat import make_admonition
from docutils import nodes


def setup(app):
    # import pdb; pdb.set_trace()
    app.add_node(otto,
                 html=(visit_todo_node, depart_todo_node),
                 latex=(visit_todo_node, depart_todo_node),
                 text=(visit_todo_node, depart_todo_node))

    app.add_directive('otto', OttoSaysDirective)


class otto(nodes.Admonition, nodes.Element):
    pass

def visit_todo_node(self, node):
    self.visit_admonition(node)

def depart_todo_node(self, node):
    self.depart_admonition(node)


class OttoSaysDirective(Directive):

    # this enables content in the directive
    has_content = True

    def run(self):
        env = self.state.document.settings.env

        targetid = "otto-%d" % env.new_serialno('otto')
        targetnode = nodes.target('', '', ids=[targetid])

        ad = make_admonition(otto, self.name, ['Autopilot Says'], self.options,
                             self.content, self.lineno, self.content_offset,
                             self.block_text, self.state, self.state_machine)
        container = nodes.container()
        container.children.extend(
            [nodes.image(uri='/images/otto-64.png')]
            + [targetnode]
            + ad
            )
        container['classes'] += ['otto-sez']
        return [container]

