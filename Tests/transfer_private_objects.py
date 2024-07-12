from TM1py.Services import TM1Service

#=====================
# a first attempt to transfer private objects of a user to probably the same user in a different TM1 model
# code work in progress, questions are added to the code
# objects in which we are interested: private subsets, views, application entries
# main difficulty for now: the script is rather slow due many calls to the REST API.
# note that:
#   impersonation is not possible in V12
#   impersonation is not possible for another admin user
#=====================

# extend the list with pairs of users (if needed)
users = [("user in source model", "comparable user in the target model")]

for user_Source, user_Target in users:

    # how to check if both users exist ?

    tm1_Source = TM1Service( address="...", port=8001, user="admin", password="...", ssl=True, impersonate=user_Source )

    private_subsets = {}
    private_views = {}
    private_application_entries = {}

    # get all private subsets on all dimensions (that the user can access)
    for d in tm1_Source.dimensions.get_all_names():
        for h in tm1_Source.dimensions.hierarchies.get_all_names(d):
            priv_subsets = tm1_Source.subsets.get_all_names(d, h, True)
            if priv_subsets:
                full_hier = "{}|{}".format(d, h)
                private_subsets.update({full_hier:priv_subsets})

    # get all private views on all cubes (that the user can access)
    for c in tm1_Source.cubes.get_all_names():
        priv_views, _ = tm1_Source.views.get_all_names(c)
        if priv_views:
            private_views.update({c:priv_views})

    # get all private application entries
    # how to retrieve these ?


    tm1_Target = TM1Service( base_url="https://CUSTOMERdev.planning-analytics.cloud.ibm.com/tm1/api/MODELNAME", user="..._tm1_automation", namespace="LDAP", password="...", ssl=True, impersonate=user_Target )

    # instead of updating or creating of private objects, maybe only do a creation if the object is new, if it is existing, leave untouched

    # loop over the private subsets and transfer them to the target server
    for full_hier, subs in private_subsets.items():
        for s in subs:
            d, h = full_hier.split('|')
            sub = tm1_Source.dimensions.subsets.get(s, d, h, True)
            private_subset = tm1_Target.dimensions.subsets.update_or_create(sub, True)

    # loop over the private views and transfer them to the target server
    for c, vws in private_views.items():
        for v in vws:
            vw = tm1_Source.cubes.views.get(c, v, True)
            private_view = tm1_Target.cubes.views.update_or_create(vw, True)
    
    # loop over the private application entries and transfer them to the target server
    # first grabbing these objects (see above)
