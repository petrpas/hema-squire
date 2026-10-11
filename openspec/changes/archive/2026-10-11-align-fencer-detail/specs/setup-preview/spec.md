## ADDED Requirements

### Requirement: The preview wears the night skin
The Setup preview SHALL render in the night skin, carrying `data-skin="night"` on its own panel, because it previews a page fencers read in that skin. The rest of the console SHALL stay day around it; nothing outside the panel changes.

#### Scenario: Preview beside the settings
- **WHEN** an organizer opens Setup on a desktop width
- **THEN** the settings are day and the preview beside them is night, its blocks, tabs and buttons drawn as the public page draws them
