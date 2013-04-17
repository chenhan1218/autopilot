from docutils import nodes
from sphinx.util.compat import Directive
from sphinx.util.compat import make_admonition


def setup(app):
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
        ad = make_admonition(otto, self.name, ['Autopilot Says'], self.options,
                             self.content, self.lineno, self.content_offset,
                             self.block_text, self.state, self.state_machine)
        image_container = nodes.container()
        image_container.children.append(nodes.image(uri='/images/otto-64.png'))
        image_container['classes'] = ['otto-image-container']
        outer_container = nodes.container()
        outer_container.children.extend(
            [image_container]
            + ad
            )
        outer_container['classes'] = ['otto-says-container']
        return [outer_container]

