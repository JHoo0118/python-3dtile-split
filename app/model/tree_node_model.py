class TreeNode:
    def __init__(self, element, level=0, node_index=0):
        self.element = element
        self.children = []
        self.name = f"{element.is_a()}"
        if element.Name is not None and element.Name != "":
            self.name += f" | {element.Name}"

        self.has_geometry = getattr(element, "Representation", None) is not None
        self.geometry = None

        self.mesh_index = None
        self.node_index = node_index
        self.level = level

    def __repr__(self):
        indent = "  " * self.level
        child = (
            f"".join([f"{child}" for child in self.children])
            if len(self.children) > 0
            else ""
        )
        return (
            f"{indent}- {self.element.is_a()} #{self.element.id()}: "
            f"{self.element.Name if hasattr(self.element, 'Name') else ''}\n"
            f"{child}"
        )