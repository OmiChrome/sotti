# Solution Block

```java
// Place this code where the stub says: import java.util.*;
class Address implements Cloneable {
    private String addr;
    public Address(String addr) { this.addr = addr; }
    public String getAddr() { return addr; }
    public void setAddr(String addr) { this.addr = addr; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return addr; }
}

class Department implements Cloneable {
    private String dept;
    public Department(String dept) { this.dept = dept; }
    public String getDept() { return dept; }
    public void setDept(String dept) { this.dept = dept; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return dept; }
}

class Person implements Cloneable {
    private String name;
    private Address addr;
    public Person(String name, Address addr) { this.name = name; this.addr = addr; }
    public String getName() { return name; }
    public Address getAddr() { return addr; }
    public Person clone() throws CloneNotSupportedException {
        Person p = (Person) super.clone();
        p.addr = (Address) this.addr.clone();
        return p;
    }
}

class Employee extends Person implements Cloneable {
    private Department dept;
    public Employee(String name, Address addr, Department dept) { super(name, addr); this.dept = dept; }
    public Department getDept() { return dept; }
    public void updateEmp(String newAddr, String newDept) {
        getAddr().setAddr(newAddr);
        this.dept.setDept(newDept);
    }
    public Employee clone() throws CloneNotSupportedException {
        Employee e = (Employee) super.clone();
        e.dept = (Department) this.dept.clone();
        return e;
    }
    public String toString() { return getName() + " : " + getAddr() + " : " + dept; }
}
```
