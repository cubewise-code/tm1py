from abc import abstractmethod


class TM1Object:
    """ Parent Class for all TM1 Objects e.g. Cube, Process, Dimension.
    
    """
    SANDBOX_DIMENSION = "Sandboxes"

    @property
    @abstractmethod
    def body(self):
        """
        Returns the body.

        Args:
            self: (todo): write your description
        """
        pass

    def __str__(self):
        """
        Returns the string representation of the message.

        Args:
            self: (todo): write your description
        """
        return self.body

    def __repr__(self):
        """
        Return a human - readable representation.

        Args:
            self: (todo): write your description
        """
        return "{}:{}".format(self.__class__.__name__, self.body)

    def __eq__(self, other):
        """
        Determine if two values.

        Args:
            self: (todo): write your description
            other: (todo): write your description
        """
        return self.body == other.body

    def __ne__(self, other):
        """
        Returns true if self and another.

        Args:
            self: (todo): write your description
            other: (todo): write your description
        """
        return self.body != other.body
