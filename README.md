# Emycin: Expert System Shell in Python

A modern Python implementation of EMYCIN (Essential MYCIN), a framework for building expert systems. This is a port and modernization of the original Python implementation by Daniel Connelly, which was based on Chapter 16 of "Paradigms of Artificial Intelligence Programming" by Peter Norvig.

Original source: [dhconnelly/paip-python](https://github.com/dhconnelly/paip-python.git)

## Overview

EMYCIN is an expert system shell that provides:
- A framework for capturing domain expert knowledge
- A backwards-chaining reasoning algorithm (similar to Prolog but with key differences)
- Mechanisms for handling uncertainty using certainty factors
- Built-in introspection capabilities for understanding system reasoning
- Interactive question-answer interface

This implementation includes MYCIN, a simple medical diagnosis expert system demonstrating EMYCIN's capabilities.

## Key Changes from Original

- Updated to work with Python 3.x (original only worked with Python 2.7)
- Improved logging configuration*
- Fixed string formatting for modern Python*
- Combined separate files to eliminate circular imports*
- Code cleanup and PEP 8 compliance*
- Improved error handling and user feedback*

## Features

- **Contexts**: Define types that the system can reason about
- **Parameters**: Specify attributes of contexts
- **Rules**: Encode expert knowledge for reasoning
- **Certainty Factors**: Handle uncertainty in knowledge and conclusions
- **Interactive Shell**: User-friendly interface for data collection and reasoning
- **Introspection**: Built-in commands to understand system's reasoning process

## Example Usage

The included MYCIN example demonstrates a medical diagnosis system:

```python
def main():
    sh = Shell()
    define_contexts(sh)
    define_params(sh)
    define_rules(sh)
    report_findings(sh.execute(['patient', 'culture', 'organism']))

if __name__ == '__main__':
    main()
```

## Interactive Commands

While using the system:
- `help`: Show available commands
- `?`: See possible values for current parameter
- `why`: Understand why a question is being asked
- `rule`: Show the current rule being applied
- `unknown`: Indicate unknown value for current parameter

## Requirements

- Python 3.x

## Acknowledgments

- Original implementation by [Daniel Connelly](http://dhconnelly.com)
- Based on work from "Paradigms of Artificial Intelligence Programming" by Peter Norvig
- Original codebase: [dhconnelly/paip-python](https://github.com/dhconnelly/paip-python.git)

## License

This project maintains the original licensing terms from dhconnelly/paip-python.

## Contributing

Feel free to submit issues and enhancement requests!
