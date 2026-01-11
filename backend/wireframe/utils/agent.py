"""
1. Delegator Agent
Chip datasheets from manufacturers typically contains one or more reference designs containing example of 
typical applications of the proposed chip. The goal of my workflow is to digest the output of 
marker-pdf analysis and extract segments of the data that pertain to each design. The indicators that
a new design is being discussed are either different paragraphs, figure mentions or others.
The goal of the manager agent is to retrieve segments of marker-pdf json and relay each segment 
to individual agents resposnible for processing single reference designs.

1. Reference Design Agent
This agent will retrieve a section of the overall PDF processing result that concerns one single
reference design. It's main goal is to:
- determine what is the name and/or use case of this design for the user's information based on textual processing
- delegate processing work to child agents
    - equation agent
    - schematic agent

2. Schematic Agent
This is a visual processing agent that deals with images of the schematic embedded within a datasheet
section. It's main challenge is to identify bounding boxes of all components present within the schematic.
For simplifcation, we can disregard wires. However, the bounding box MUST include the component itself 
AND it's label, which can either be a variable name (like C1 or R2 etc) with or without additional text (like "COMPONENSATION CS" or "(PARASITIC)")
It's not completely clear on how to match component with its label because sometimes the two are not directly next to each other, though generally,
this can be determined based on proximity evaluation and label type (closes alphanumeric (and non fully numeric because these are most likely pin numbers of another chip)) is the correct label
Once the agent identifies a list of all bounding boxes, each of them is passed to the symbol identifier agent. You should explore state of the art solutions for this problem.

3. Equation Agent
Equation agent retrieves all equations present within a certain datasheet section, as well
as any supporting information. Here is an example of what you could find:

"The high-voltage bus is sensed by a voltage divider, which consists
of the R1 and the R2. As described in the previous section, the
VOUT1 voltage follows the VIN+ with a typical gain of 1.
When monitoring very high bus voltages, the parasitic capacitances
of the R1 can impose a risk of overvoltage spikes on the VIN+
during switching events on the VBUS. The recommendation is to
connect a compensation capacitor C2 in parallel to the R2. Proper
compensation is achieved by selecting C2 such that
C2 = R1 x C1/R2 (1)
The value of C2 is not critical but must be selected slightly higher
than the calculated value to suppress any overshoot on the VIN+
during the switching events on the VBUS. For example, if VBUSmax = 1 kV DC and VOUT = 4.3 V, the required divider ratio is
approximately 1/233, where R1 = 2 MΩ and R2 = 8.62 kΩ. With
an estimated parasitic capacitance C1 of approximately 10 pF, the
compensation capacitance becomes C2 ≥ 2.3 nF."

This agent will need to interpret the equations and use a computation tool to deterministically find correct values

4. Symbol Agent
The sole purpose of this agent is to digest a bounding box containing a chip symbol from
a reference design and determine it's function/type like: resistor, capacitor, diode, opamp etc.
There are a few different ways to go about it:
    1. Determine the type based on specified constraint unit - if the bouding box contains a constraint in form of a given 
    physical unit like "100nF", we would know it must be a capacitor
    2. If it contains a variable name, we could infer the type from the contex of the datasheet segment in which
    it is mentioned
        - this would delegate the work to Textual Processing Agent with an instruction to look for that name
    3. If these are not available, use a vision classifier

5. The Problem

5.1 
The most important issue that has to be solved is correct component selection and Kicad schematic generation for a user-specified reference design.
To simplify, the user should be able to select one or more of the agent-detected reference designs and then retrieve an equivalent Kicad schematic.
To that end the most crucial aspect is determining correct component constraints based on user specified parameters.
Components in the reference design can be classified into several categories based on importance:
- value of the component is not important and can be any compoennt of a given type (resistor with any resistance, capacitor with any capacitance etc)
- value for the component needs to be very specific and is independent of external variables (like a capacitor which must be exactly 100nF)
- component value is governed by an equation that depends on the combination of value of other components and/or external variables (for example it depends on V_IN which is user specified)
- component value is circumstantial, depending on textual daspecification present within the datasheet and requires additional context, for example:
    "The value of C2 is not critical but must be selected slightly higher
    than the calculated value to suppress any overshoot on the VIN+
    during the switching events on the VBUS. For example, if VBUSmax = 1 kV DC and VOUT = 4.3 V, the required divider ratio is
    approximately 1/233, where R1 = 2 MΩ and R2 = 8.62 kΩ. With
    an estimated parasitic capacitance C1 of approximately 10 pF, the
    compensation capacitance becomes C2 ≥ 2.3 nF.",
   in which case the value must be slightly higher than what the formula computes, but it could only be inferred from the textual context

5.2 
The LLM agent has to determine which variables in the datasheet can be treated as requiring user input and being design-dependent.
These variables will require input from the user who engages in the datasheet processing in a human-in-the-lopp prcoess. 
Input for these variables will be used to determine the constraints of components based on the paradigm explained in the subpoints above and fetch
the correct symbols. The application doesnt need to solve the problem of actualy finding chip symbols with given constraints as this functionality will be
provided by an already implemented API which takes a dictionary of filter name: value pairs.
The main problem to solve is actual inference of constraints from the datasheet, for which
Equation Agents and Symbol Identifier Agents will require exteremly strict collaboration.

Requirements:
1. Failure of one agent should not affect the workflow of unrelated agents. For example,
if the datasheet has two reference designs, failure to process one should not cause entire processing to fail if 
the other one succeeds. Similarly on a lower level, for example if constraints of one component within a reference design
could not be determined, it should not stop other agents from working on other components. However, the user must be aware what fails 
and what doesn't.
2. Reliability takes precedence over speed
3. The symbols in the generated schematic absoltely have to contain pointers to specific datasheet segments that 
govern how the constraints of the chip was determined (according to paradigm explained in section 5.1)
4. For an MVP, creating a netlist and connections within the output Kicad schematic will not be needed as it's a difficult problem. 

"""