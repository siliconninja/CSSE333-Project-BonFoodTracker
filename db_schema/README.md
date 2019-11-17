# DB Schema Documentation

## ER Diagram (Rose-Hulman Standard)
A square means entity.

An ellipse means an attribute.

An underline means a primary key of that particular entity.

A diamond means relationship (or relationship table).

A number above/below/to the left of/to the right of the line to a relationship means the cardinality of that entity in the relationship.

Specifically:
    
- 1 means the entity can form 1 or more set(s) of unique row(s) in the relationship (but only 1 of that type of row can exist), depending on the cardinality of the other side.

- N means the entity can form 1 or more set(s) of unique row(s) in the relationship (but **more than 1** of that type of row can exist), depending on the cardinality of the other side.

Double line means mandatory participation in this relationship for that particular entity (i.e. the reference to the row in the entity in the relationship table cannot be NULL for the entity row to exist).

## Relational Schema (Rose-Hulman Standard)

The entity or relationship name (which is slightly different to indicate the way we name our table names) is shown on the left hand side of each table.

The attribute(s) of the entity/relationship (meaning columns in a table, and are is slightly different to indicate the way we name our relationships) are shown to the right of the entity/relationship name in each table.

An underline means a primary key of that particular entity/relationship.

**Arrows in the relational schema indicate foreign keys.** 
