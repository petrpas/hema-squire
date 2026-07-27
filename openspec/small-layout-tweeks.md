1. register form
     - not very useful to have two lines for name in one form, lets reuse the first one in the search 
     - before linking the user with hema ratings id, ask user explicitely, if he confirms, this account is his. put a link to the hemarating and all details in the confirmation box, so he is sure.
     - change the string "HEMA Ratings profile confirmed: Petr Lukeš" to "HEMA Ratings profile confirmed: Petr Lukeš (8956)"
2. list of opened tournaments
     - padding from left and right in the box - 1 em
     - add tournament logo both as a data field (probably not in sqlite but a file in a filesystem with filename in the table)
       - logo should be added in tourmanet settings
       - logo should be shown on the left of the tournament box in the list
     - find a way to list the date and place a bit more graphicly emphsized not as a one long line but perhaps as a multiple column layout that automatically adjust for smaller screens 
     - the tournamnet should have the option to set a subtitle, possibly longer than tournament name itself but frequently empty, layouts should work with both options
3. Tournament registraion
     - split into two screens:
     - (1) tournament details - opened from the list of tournaments
       - list of disciplines
         - for each discipline
           - name, capacity, registered e.g. Longsword Open    15/72 fencers
           - when and where (optional, mainly for multiday actions): e.g. Saturday, Main Hall - Kurtzstrasse 21
           - ruleset (short name of ruleset style e.g. Right of Way, see [link](link to external document) - optional field
       - other actions 
         - like seminars, afterparties, aftersparrings, or perhaps accomodation
         - name, when and where, remark - optional
       - do not mention gear lending or merch on this page. 
     - (2) Register
       - only available if the tournament is opened and a discipline or other action has open slot
       - list everything available as a long list
       - sections given by types of offer
         - tournament
         - actions
         - gear lending
         - merch and other stuff 
         - you can offer more proper names for the categories


 