

class TM1Object:
    """ Parent Class for all TM1 Objects e.g. Cube, Process, Dimension.
    
    """
    SANDBOX_DIMENSION = "Sandboxes"

    @property
    def body(self):
        pass

    def __str__(self):
        return self.body

    def __repr__(self):
        return "{}:{}".format(self.__class__.__name__, self.body)

    def __eq__(self, other):
        return self.body == other.body

    def __ne__(self, other):
        return self.body != other.body
