

def get_breadcrumb(category):
    """
    获取面包屑导航
    :param category:  类别对象：一级，二级，三级
    :return: 传递的category是一级：返回一级；
            传递caetgory为二级：返回一级+二级；
             caetgory为三级：返回一级+二级+三级

    """

    breadcrumb = {
        'cat1': '',
        'cat2': '',
        'cat3': ''
    }

    # 一级类别没有父级
    if category.parent == None:  # 说明category是一级
        breadcrumb['cat1'] = category # 将一级类别赋值给 cat1
        # 三级类别下面没有子级，说明category是三级
    elif category.subs.count() == 0:
        cat2 = category.parent # 通过三级查询二级
        breadcrumb['cat1'] = cat2.parent # 取出一级类别并赋值给cat1
        breadcrumb['cat2'] = cat2 # 将二级类别赋值给cat2
        breadcrumb['cat3'] = category # 将三级类别赋值给cat3
    else:  # 说明category是二级
        breadcrumb['cat1'] = category.parent # 子查父 category.parent查询一级
        breadcrumb['cat2'] = category # 将一级分类赋值给cat2
    return breadcrumb
