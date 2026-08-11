Current tournament settings are a bit too complex.

Motivation: We want to make the interface simpler for first-time users and organizers of smaller tournaments.

Let's separate simple tournaments with one or two disciplines from large-scale tournaments.

When creating a new tournament, after the first modal, you should get a second modal—let's call it "Tournament Mode":

Radio buttons:
() Easy mode - simple tournament with no advanced features
() Advanced mode - enable one or more of:
  [ ] Tournament schedule (disciplines specify where and when they occur)
     ℹ For larger tournaments with multiple disciplines on different days and in different locations
  [ ] Payments
     ℹ I want to use HEMA Squire to handle payment processing
  [ ] Team disciplines
     ℹ Tournament includes one or more team disciplines
  [ ] Extra services (after-party, seminars, weapon lending, merchandise)

This second modal can also be opened via a button in the Settings section:

OTHER > TOURNAMENT SETTINGS MODE: Easy mode [CHANGE]

The mode setting only affects the UI, not the functionality. Settings are simply hidden and deactivated but not changed. Returning to advanced mode displays the advanced options again.

Regarding payments: when payments are disabled, disciplines still retain prices in the selected currency, and discounts remain possible. We simply don't expect to handle payment processing.

After-parties and seminars retain location and time information even when the schedule is disabled.