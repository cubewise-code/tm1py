from Objects.Annotation import Annotation
from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.AnnotationService import AnnotationService
import uuid

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
tm1_rest = RESTService(ip='', port=8001, login=login, ssl=False)
annotation_service = AnnotationService(tm1_rest)

# just a random text
random_string = str(uuid.uuid4())

# create instance of TM1py.Annotation
a = Annotation(comment_value=random_string,
               object_name='plan_BudgetPlan',
               dimensional_context=['FY 2004 Forecast', '10110', '110', '61065','planning', 'revenue (future)',
                                    'Jan-2005'])

# create annotation on TM1 Server
annotation_service.create(a)

# find the created annotation and delete it
for annotation in annotation_service.get_all('plan_BudgetPlan'):
    if annotation.comment_value == random_string:
        annotation_service.delete(annotation_id=annotation.id)

# logout
tm1_rest.logout()
