# Tasks

#### Market structure value areas analysis

- [ ] put analysis execution flow in order so that value areas are calculated before market structure, so that market structure can use value areas to set the market_structure.value_areas field to one of the following:

ASCENDING
DESCENDING
NEUTRAL

To determine the market structure value areas, it should analyse whether the value areas as price progresses are ascending or descending. Look at the last 3 value areas, specially the POCs, and analyse them in a similar way as it does with the pivot points for market structure. If the last 3 value areas are ascending, then the market structure value areas are ascending. If the last 3 value areas are descending, then the market structure value areas are descending. If the last 3 value areas are mixed up, then the market structure value areas are neutral.


#### Analysis Object Documentation

- [ ] Update documentation on the analysis object by improving the text in the docs/ folder. 
- [ ] Re-generate the schema html by running the command mentioned in the README.md file.
- [ ] Update the analysis object documentation in the docs/ folder to include any new/modified fields added to the analysis object.


#### Cleaner Documentation

- [ ] Update the documentation in the docs/ folder to be more concise and easier to read. Remove any duplicate information and group content into easy to navigate sections.


#### UI UX

- [ ] Update the UI to have more colors in the Intelligence tab to make it more visually appealing and easier to read the analysis object parameters and values.


#### Logging

- [ ] Ensure that all the logging is done in the correct format and that it is easy to read and understand. Ensure all LLM Agent calls are properly logged for debugging and analysis.
- [ ] Ensure market agent calls are logged in a way that is easy to read and understand.

#### Spare prompts/folder

- [ ] There is a prompts/ folder with a file called init.md. Move the contents of this file to the docs/ folder, into the appropriate section, and remove the prompts/ folder. There should only be one prompts/ folder in the project and it is the one with all the LLM agent call prompts.

