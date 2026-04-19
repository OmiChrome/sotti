# Solution Block

```java
public boolean isEligible() {
        long diff = (dose_two.getTime() - dose_one.getTime()) / (1000 * 60 * 60 * 24);
        return diff >= 28;
    }
}

//Define class StudentList here.
class StudentList {
    //Inside class StudentList, define method getEligibleList(List<Student>)
    //that uses the method isEligible() in class Student to return the
    //stream of eligible students.
    public Stream<Student> getEligibleList(List<Student> list) {
        return list.stream().filter(Student::isEligible);
    }

    //Define method isEmpty(Stream<Student>)
    //that helps customizing output message
    public boolean isEmpty(Stream<Student> stream) {
        return stream.findAny().isEmpty();
    }
}
```
