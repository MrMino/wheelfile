from wheelfile import WheelFile

foo1 = WheelFile('path/to/your/wheel')
foo2 = WheelFile(
    '/path/to/dir/where/foo2/wheel/should/be/created/',
    distname=foo1.distname,
    version=str(foo1.version) + "+myversion",
    build_tag=foo1.build_tag,
    language_tag=foo1.language_tag,
    abi_tag=foo1.abi_tag,
    platform_tag=foo1.platform_tag,
    mode='w')

foo2.metadata = foo1.metadata
foo2.metadata.version = foo2.version

foo2.wheeldata.root_is_purelib = foo1.wheeldata.root_is_purelib
foo2.wheeldata.tags = foo1.wheeldata.tags

for zinfo in foo1.infolist():
    arcname = zinfo.filename

    arcname_head, *arcname_tail = arcname.split('/')
    arcname_tail = '/'.join(arcname_tail)
    if arcname_head == foo1.distinfo_dirname:
        new_arcname = foo2.distinfo_dirname + '/' + arcname_tail
        foo2.writestr(new_arcname, foo1.zipfile.read(zinfo))
        continue
    if arcname_head == foo1.data_dirname:
        new_arcname = foo2.data_dirname + '/' + arcname_tail
        foo2.writestr(new_arcname, foo1.zipfile.read(zinfo))
        continue

    foo2.writestr(zinfo, foo1.zipfile.read(zinfo))
foo2.close()
