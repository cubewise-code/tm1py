from TM1py import TM1Queries, Annotation
import uuid

# connection to TM1 Server
q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)

# just a random text
random_string = str(uuid.uuid4())

a = Annotation(comment_value=random_string, object_name='plan_BudgetPlan',
               dimensional_context=['FY 2004 Forecast', '10110', '110', '61065',
                                    'planning', 'revenue (future)', 'Jan-2005'])

# post annotation on TM1 Server
print(q.create_annotation(a))

# find the created annotation and delete it
for annotation in q.get_all_annotations_from_cube('plan_BudgetPlan'):
    if annotation.get_comment_value() == random_string:
        q.delete_annotation(annotation._id)

# logout
q.logout()
