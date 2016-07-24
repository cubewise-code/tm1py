from TM1py import TM1pyQueries as TM1, TM1pyLogin, Annotation
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# just a random text
random_string = str(uuid.uuid4())

# create instance of TM1py.Annotation
a = Annotation(comment_value=random_string,
               object_name='plan_BudgetPlan',
               dimensional_context=['FY 2004 Forecast', '10110', '110', '61065',
                                    'planning', 'revenue (future)', 'Jan-2005'])

# create annotation on TM1 Server
tm1.create_annotation(a)

# find the created annotation and delete it
for annotation in tm1.get_all_annotations_from_cube('plan_BudgetPlan'):
    if annotation.get_comment_value() == random_string:
        tm1.delete_annotation(id=annotation.get_id())

# logout
tm1.logout()
