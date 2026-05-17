[cook] <tag:me@example.com,2026:recipes:>

## Apple Pie {=cook:apple-pie .Recipe label}

Description: **Classic homemade apple pie** {comment}
Cooking time: **45** {cook:cookTime ^^xsd:integer} minutes
Servings: **8** {cook:recipeYield ^^xsd:integer}
Difficulty: **Medium** {cook:difficulty}

Ingredients:

* Apples    {+cook:apples    ?cook:recipeIngredient .cook:Ingredient label}
* Sugar     {+cook:sugar     ?cook:recipeIngredient .cook:Ingredient label}
* Butter    {+cook:butter    ?cook:recipeIngredient .cook:Ingredient label}
* Flour     {+cook:flour     ?cook:recipeIngredient .cook:Ingredient label}
* Cinnamon  {+cook:cinnamon  ?cook:recipeIngredient .cook:Ingredient label}

_Ingredient_ {=cook:Ingredient .Class label} — class for items in the
**Cookbook** {!member +urn:collection:cookbook .Container label}.

Equipment:

* Oven         {+cook:oven-1  ?cook:requiresEquipment .cook:Device  label}
* Mixing bowl  {+cook:bowl-1  ?cook:requiresEquipment .cook:Utensil label}
* Rolling pin  {+cook:pin-1   ?cook:requiresEquipment .cook:Utensil label}

Calories: [1235] {cook:calories ^^xsd:integer} kcal
Sugar:    [40]   {cook:sugarGrams ^^xsd:decimal} grams

Related recipes:

* Apple Crumble {+cook:apple-crumble !cook:variationOf .cook:Recipe label}
* Peach Pie     {+cook:peach-pie     !cook:variationOf .cook:Recipe label}
